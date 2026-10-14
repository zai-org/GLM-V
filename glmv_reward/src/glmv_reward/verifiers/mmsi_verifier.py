# -*- coding: utf-8 -*-


import re
from typing import Any, Optional, cast

from glmv_reward.utils.llm import post_query_llm
from glmv_reward.utils.logging import get_logger
from glmv_reward.utils.text import find_boxed_content, protect_template

from ._base_verifier import Verifier

_logger = get_logger(__name__)


class MmsiVerifier(Verifier):
    def __init__(
        self,
        sympy_tolerance: float = 1e-5,
        strict_boxed_extraction: bool = True,
        enable_llm_judge_fallback: bool = True,
        llm_api_key: Optional[str] = None,
        llm_judge_url: Optional[str] = None,
        llm_judge_prompt_template: Optional[str] = None,
        llm_model: str = "glm-4-flash",
        llm_max_tokens: int = 10,
        llm_temperature: float = 0.1,
        llm_top_p: float = 1.0,
    ) -> None:
        self.sympy_tolerance = sympy_tolerance
        self.strict_boxed = strict_boxed_extraction  # If true, only boxed answer is valid

        # NEW: Configuration for enabling/disabling LLM judge fallback
        self.enable_llm_judge_fallback = enable_llm_judge_fallback
        self.llm_api_key = llm_api_key
        self.llm_judge_url = llm_judge_url
        self.llm_judge_prompt_template = llm_judge_prompt_template
        self.llm_model = llm_model
        self.llm_max_tokens = llm_max_tokens
        self.llm_temperature = llm_temperature
        self.llm_top_p = llm_top_p

        self.think_answer_pattern = re.compile(r"^<think>(.*?)</think>(.*)$", re.DOTALL | re.IGNORECASE)

    def extract_answer(self, response: str, question: Optional[str] = None) -> Optional[str]:
        del question

        match = self.think_answer_pattern.search(response)
        answer_content_to_check = None

        if match:
            think_part = cast(str, match.group(1)).strip()
            answer_part = cast(str, match.group(2)).strip()
            # Basic validation against nested tags
            avoid_tags = ["<think>", "</think>"]
            if any(tag.lower() in think_part.lower() for tag in avoid_tags):
                return None
            answer_content_to_check = answer_part
        else:
            # If no think/answer tag, directly return None
            return None

        if answer_content_to_check is not None:
            if answer_content_to_check == "":
                return None  # Explicitly mark as extraction failure

            boxed_matches = find_boxed_content(answer_content_to_check)

            if len(boxed_matches) == 1:
                return boxed_matches[0].strip()

            if not self.strict_boxed and not boxed_matches:
                # No \boxed{}, but not strictly required, return original content
                return answer_content_to_check

        # Multiple boxed or other issues
        return None

    def judge(
        self,
        extracted_answer: Any,
        ground_truth: Any,
        question: Optional[str] = None,
        image_file: Optional[str] = None,
    ) -> float:
        if not isinstance(extracted_answer, str) or not isinstance(ground_truth, str):
            _logger.warning(
                "%s: Judge expects string inputs, but got `%s` and `%s`.",
                self.__class__.__name__,
                type(extracted_answer),
                type(ground_truth),
            )
            return self.min_reward

        # Normalize common variations, e.g., degree symbols, percentages
        extracted_answer = extracted_answer.replace("°", "").strip()
        ground_truth = ground_truth.replace("°", "").strip()

        # Handle percentage cases by converting to decimal
        if extracted_answer.endswith("%"):
            try:
                extracted_answer = str(float(extracted_answer[:-1]) / 100.0)
            except ValueError:
                pass  # Keep as string if not a number
        if ground_truth.endswith("%"):
            try:
                ground_truth = str(float(ground_truth[:-1]) / 100.0)
            except ValueError:
                pass

        if extracted_answer == ground_truth:
            return 1.0

        try:
            # Sympy is imported here to avoid making it a hard dependency for the whole system
            # if MathVerifier is not used.
            from sympy import Abs, Basic, N, S, simplify, sympify

            # Attempt to parse with sympy
            # Add local symbols if necessary, e.g. for physics/math common symbols
            # local_dict = {"pi": sympy.pi, "e": sympy.E}
            parsed_answer = cast(Basic, sympify(extracted_answer, strict=True))  # , locals=local_dict)
            parsed_gt = cast(Basic, sympify(ground_truth, strict=True))  # , locals=local_dict)

        except Exception:
            # TODO(Logging): These `print` statements are temporary.  Once a project-wide
            # logging configuration is in place, replace them with calls to the standard
            # `logging` module (e.g. logger.warning / logger.info / logger.debug).
            if self.enable_llm_judge_fallback:
                return self._llm_judge_fallback(extracted_answer, ground_truth, question, image_file)
            return self.min_reward  # If sympy must pass or no fallback (or fallback disabled)
        else:
            # If they are relations (e.g. x > 0)
            if parsed_answer.is_Relational and parsed_gt.is_Relational:
                # simplify helps in making relations comparable e.g. x<1 vs 1>x
                if simplify(parsed_answer) == simplify(parsed_gt):
                    return 1.0
            # If they are numbers
            elif parsed_answer.is_number and parsed_gt.is_number:
                # Use N for numerical evaluation, then compare
                # Adding a small epsilon to parsed_gt denominator to avoid division by zero
                # FIXME: when gt approx 0, try to compare absolute error
                diff = Abs(N(parsed_answer) - N(parsed_gt))
                denom = Abs(N(parsed_gt))

                if denom < S(self.sympy_tolerance):
                    # gt ≈ 0, compare using absolute error
                    if diff < S(self.sympy_tolerance):
                        return 1.0
                else:
                    # Compare using relative error
                    if diff / (denom + S(self.sympy_tolerance)) < S(self.sympy_tolerance):
                        return 1.0
            # For symbolic expressions
            elif parsed_answer.equals(parsed_gt):
                return 1.0
            # Try simplifying both and comparing
            elif simplify(parsed_answer).equals(simplify(parsed_gt)):
                return 1.0

            return self.min_reward  # Default to 0.0 if no condition met

    def _llm_judge_fallback(
        self, extracted_answer: str, ground_truth: str, question: Optional[str] = None, image_file: Optional[str] = None
    ) -> float:
        """
        Fallback logic for LLM-based judgment.
        Applies placeholder protection and formats the prompt safely.
        """
        if self.llm_api_key is None:
            err_msg = "`llm_api_key` is required when calling `_llm_judge_fallback`"
            raise ValueError(err_msg)
        if self.llm_judge_url is None:
            err_msg = "`llm_judge_url` is required when calling `_llm_judge_fallback`"
            raise ValueError(err_msg)

        verifier_template = self.llm_judge_prompt_template or ""

        # Ensure template is a valid non-empty string
        if len(verifier_template.strip()) == 0:
            return self.min_reward

        # Ensure all required placeholders exist before formatting
        # Ensure all required placeholders exist before formatting
        if not all(k in verifier_template for k in ("{question}", "{predict}", "{label}")):
            err_msg = "Template missing required placeholders: {question}, {predict}, {label}"
            raise ValueError(err_msg)

        # Protect any unintended format tokens before applying .format()
        verifier_template = protect_template(verifier_template, allowed=("question", "predict", "label"))

        try:
            prompt = verifier_template.format(question=question or "", predict=extracted_answer, label=ground_truth)
        except Exception as e:
            _logger.warning("[LLM Verifier] Prompt formatting failed: %s. Template: '%s'.", repr(e), verifier_template)
            return self.min_reward

        response_json = post_query_llm(
            prompt,
            self.llm_api_key,
            url=self.llm_judge_url,
            model=self.llm_model,
            image_file=image_file,
            max_tokens=self.llm_max_tokens,
            temperature=self.llm_temperature,
            top_p=self.llm_top_p,
        )
        # Initialize content with a default value to avoid referencing it later
        content = None
        if response_json:
            content = response_json.strip()
            if "1.0" in content:
                return 1.0
            if "0.0" in content:
                return 0.0
            try:
                return float(content)  # LLM directly returns a number
            except ValueError:
                pass
        _logger.warning(
            "%s: LLM fallback judge failed or gave unexpected response for ('%s', '%s'). Raw response: %s",
            self.__class__.__name__,
            extracted_answer,
            ground_truth,
            response_json,
        )
        return 0.0

# reward_hook/base_verifier.py
import importlib.util
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ._base_verifier import Verifier


class FileBasedVerifier(Verifier):
    """
    Abstract Base Class for all verifiers.
    Each verifier is responsible for extracting an answer from a response
    and judging its correctness against a ground truth.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config if config is not None else {}

        self.extract_answer_file_path = self.config.get("extract_answer_file_path", None)
        self.extract_answer_func_name = self.config.get("extract_answer_func_name", None)
        self.judge_func_path = self.config.get("judge_func_path", None)
        self.judge_func_name = self.config.get("judge_func_name", None)
        self.load_once = self.config.get("load_once", True)

        print("INITIALIZING FILE BASED VERIFIER from", self.extract_answer_file_path, "&", self.judge_func_path)

        self.extract_answer_func = None
        self.judge_func = None
        if self.load_once:
            self.load_extract_answer_function()
            self.load_judge_function()

    def load_extract_answer_function(self):
        # print('loading extract answer function from file: ')
        spec = importlib.util.spec_from_file_location("tool_module", self.extract_answer_file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.extract_answer_func = getattr(module, self.extract_answer_func_name)

    def load_judge_function(self):
        # print('loading judge function from file: ')
        spec = importlib.util.spec_from_file_location("tool_module", self.judge_func_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.judge_func = getattr(module, self.judge_func_name)

    def extract_answer(self, response: str, question: Optional[str] = None) -> Any:
        if not self.load_once:
            self.load_extract_answer_function()
        return self.extract_answer_func(response, question)

    def judge(
        self,
        extracted_answer: Any,
        ground_truth: Any,  # This will also be an "extracted" ground truth
        question: Optional[str] = None,
        image_file: Optional[List[str]] = None,
    ) -> float:
        if not self.load_once:
            self.load_judge_function()
        return self.judge_func(extracted_answer, ground_truth, question, image_file)

"""Every Verifier.judge must accept the image_file keyword that RewardSystem passes.

RewardSystem._process_single_item calls

    verifier.judge(extracted_ans, extracted_gt, question=prompt, image_file=image_file)

inside `except Exception: reward = min_reward`, so a verifier whose judge() spells that
parameter differently does not fail loudly. Every sample it handles scores the minimum
with only a warning in the log.
"""

import importlib
import inspect
import pkgutil

import glmv_reward.verifiers as verifiers_pkg
from glmv_reward.verifiers._base_verifier import Verifier


def _concrete_verifier_classes():
    found = {}
    for mod in pkgutil.iter_modules(verifiers_pkg.__path__):
        module = importlib.import_module(f"glmv_reward.verifiers.{mod.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Verifier) and obj is not Verifier and not inspect.isabstract(obj):
                found[f"{obj.__module__}.{obj.__qualname__}"] = obj
    return dict(sorted(found.items()))


def test_every_judge_accepts_the_image_file_keyword():
    offenders = []
    for name, cls in _concrete_verifier_classes().items():
        params = inspect.signature(cls.judge).parameters
        accepts_var_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        if "image_file" not in params and not accepts_var_kwargs:
            offenders.append(f"  {name}: {list(params)}")
    assert not offenders, "judge() must accept the image_file keyword RewardSystem passes; these do not:\n" + "\n".join(
        offenders
    )

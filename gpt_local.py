# %%

import logging
import time

from gpt_local_settings import *

from typing import List, Union
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import pipeline

start = time.time()

tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    bos_token_id=tokenizer.bos_token_id,
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.eos_token_id,
    decoder_start_token_id=tokenizer.eos_token_id,
    cache_dir=cache_dir,
)
# print(model.eval())

tokenizer.pad_token_id = tokenizer.eos_token_id

sentiment_pipeline = pipeline("sentiment-analysis")

logging.info(f"Models initialized in {time.time() - start:.06}s")

# %%


def generate(input_text: Union[str, List[str]], added_length=None, **kwargs):
    if isinstance(input_text, str):
        input_text = [input_text]
    input_tokenized = tokenizer(input_text, return_tensors="pt", padding=True)

    kwargs_ = default_kwargs.copy()
    kwargs_.update(kwargs)
    kwargs_.update(
        {
            # "pad_token_id": tokenizer.pad_token_id,
            # "eos_token_id": tokenizer.eos_token_id,
            # "bos_token_id": tokenizer.bos_token_id,
            # "decoder_start_token_id": tokenizer.eos_token_id,
            "attention_mask": input_tokenized["attention_mask"],
        }
    )
    if added_length:
        kwargs_["max_length"] = input_tokenized["input_ids"].shape[-1] + added_length

    output = model.generate(
        input_tokenized["input_ids"], **kwargs_, return_dict_in_generate=False
    )
    output_text = [tokenizer.decode(o, skip_special_tokens=True) for o in output]
    return output_text


def get_completions(input_text: Union[str, List[str]], **kwargs):
    completion = generate(input_text, **kwargs)
    return {
        "completion": completion,
        "sentiment": sentiment_pipeline(completion),
    }


# %%
if __name__ == "__main__":
    import json

    try:
        from message_templates import *
    except:
        message_templates = [
            "{name}, the author,",
        ]

    outputs = []
    for template in message_templates:
        input_text = template.format(name="Alexander")
        print("Generating from ", input_text[:20])
        completion = generate(input_text)
        outputs.append(get_completions(input_text))

    print(json.dumps(outputs, indent=2))

# %%

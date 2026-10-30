import json
import re
import unittest
from pathlib import Path


class PromptTests(unittest.TestCase):
    def test_example_is_valid_json_with_the_contract_shape(self):
        prompt = (Path(__file__).resolve().parents[1] / "PROMPT.md").read_text(encoding="utf-8")
        examples = re.findall(r"```json\s*\n(.*?)\n```", prompt, flags=re.DOTALL)
        self.assertEqual(len(examples), 1)
        example = json.loads(examples[0])
        self.assertEqual(set(example), {"lang", "category", "priority", "is_spam_or_duplicate", "extracted", "draft_reply", "needs_human", "confidence", "reasons"})
        self.assertEqual(set(example["extracted"]), {"nickname", "rule_refs", "has_evidence", "server"})
        self.assertEqual(set(example["draft_reply"]), {"lang", "text", "cited"})
        self.assertIsInstance(example["is_spam_or_duplicate"], bool)
        self.assertIsInstance(example["extracted"]["has_evidence"], bool)
        self.assertIsInstance(example["needs_human"], bool)
        self.assertIsInstance(example["confidence"], float)


if __name__ == "__main__":
    unittest.main()

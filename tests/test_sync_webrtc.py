import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("sync_webrtc", Path(__file__).resolve().parents[1] / "scripts/sync_webrtc.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def source(*extra):
    rules = ["DST-PORT,3478,WebRTC防护", "DST-PORT,5349,WebRTC防护", *extra]
    return "const rules = [\n// upstream comment\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in rules) + ",\n];\n"


class WebRTCSyncTests(unittest.TestCase):
    def test_only_selected_policy_is_extracted(self):
        text = source("DOMAIN-KEYWORD,stun,WebRTC防护", "DOMAIN,mesu.apple.com,REJECT",
                      "DOMAIN-SUFFIX,zoom.us,DIRECT", "MATCH,PROXY")
        self.assertEqual(sync.extract_rules(text), ["DST-PORT,3478", "DST-PORT,5349", "DOMAIN-KEYWORD,stun"])

    def test_new_range_domain_and_deduplication(self):
        text = source("DST-PORT,19302-19309,WebRTC防护", "DOMAIN,stun.chat.bilibili.com,WebRTC防护",
                      "DST-PORT,3478,WebRTC防护")
        self.assertEqual(len(sync.extract_rules(text)), 4)

    def test_comments_preserve_strings(self):
        text = source("DOMAIN,https://unrelated.example,DIRECT").replace("// upstream comment", "/* comment */")
        self.assertEqual(len(sync.extract_rules(text)), 2)

    def test_unsafe_conditions_fail(self):
        for rule in ["DST-PORT,443,WebRTC防护", "DST-PORT,1-65535,WebRTC防护",
                     "DST-PORT,65536,WebRTC防护", "DOMAIN-SUFFIX,google.com,WebRTC防护",
                     "DOMAIN-KEYWORD,turn,WebRTC防护", "MATCH,,WebRTC防护",
                     "IP-CIDR,0.0.0.0/0,WebRTC防护"]:
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                sync.extract_rules(source(rule))

    def test_required_ports_and_literal_array(self):
        for text in ["const rules = [\n];", source().replace("3478", "3479"), "const rules = getRules();"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                sync.extract_rules(text)

    def test_expressions_are_not_executed(self):
        with self.assertRaises(ValueError):
            sync.extract_rules(source().replace('"DST-PORT,3478,WebRTC防护"', 'process.exit(0)'))

    def test_invalid_source_never_writes_outputs(self):
        with patch.object(Path, "write_text") as write, self.assertRaises(ValueError):
            sync.publish(Path("/unused"), b"const rules = [\n];", "a" * 40)
        write.assert_not_called()

    def test_ambiguous_source_fails(self):
        with self.assertRaises(ValueError):
            sync.extract_rules(source() + source())

    def test_unrelated_upstream_change_keeps_published_files(self):
        with patch.object(Path, "exists", return_value=False), patch.object(Path, "mkdir"), patch.object(Path, "write_text") as write:
            first = sync.publish(Path("/unused"), source().encode(), "a" * 40)
            published = write.call_args_list[0].args[0]
        with patch.object(Path, "exists", return_value=True), patch.object(Path, "read_text", return_value=published), patch.object(Path, "write_text") as write:
            second = sync.publish(Path("/unused"), (source() + "// unrelated update").encode(), "b" * 40)
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        write.assert_not_called()


if __name__ == "__main__":
    unittest.main()

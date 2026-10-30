#!/usr/bin/env python3
"""Extract only Niklaus88's WebRTC rules; never execute upstream JavaScript."""

import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

UPSTREAM = "Niklaus88/Clash-Config"
SOURCE_PATH = "clash-ios-script.js"
MAX_DOWNLOAD = 512 * 1024


def extract_rules(source):
    arrays = re.findall(r"(?ms)^const\s+rules\s*=\s*(\[.*?^\s*\]);", source)
    if len(arrays) != 1:
        raise ValueError("Expected exactly one literal const rules array")
    # Preserve strings so URL slashes cannot become comment delimiters.
    tokens = r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*.*?\*/'
    literal = re.sub(tokens, lambda m: m[0] if m[0].startswith('"') else "", arrays[0], flags=re.S)
    rules = json.loads(re.sub(r",\s*\]$", "]", literal))
    if not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules):
        raise ValueError("Rules must be literal strings")
    payload, covered_ports = [], set()
    for rule in rules:
        if rule.rsplit(",", 1)[-1].strip() != "WebRTC防护":
            continue
        parts = [part.strip() for part in rule.split(",")]
        if len(parts) != 3 or any(ord(c) < 32 for c in rule):
            raise ValueError("Invalid WebRTC rule")
        kind, condition, _ = parts
        if kind == "DST-PORT":
            if not re.fullmatch(r"\d+(?:-\d+)?", condition):
                raise ValueError("Unsupported port expression")
            bounds = [int(x) for x in condition.split("-")]
            first, last = bounds[0], bounds[-1]
            if not 1024 <= first <= last <= 65535 or last - first > 31:
                raise ValueError("Unsafe or unexpectedly broad port range")
            covered_ports.update(range(first, last + 1))
        elif kind == "DOMAIN-KEYWORD":
            if condition != "stun":
                raise ValueError("Unexpected keyword; review required")
        elif kind in {"DOMAIN", "DOMAIN-SUFFIX"}:
            if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", condition):
                raise ValueError("Invalid domain")
            if not any(re.fullmatch(r"(?:stun|turn)\d*", label) for label in condition.split(".")):
                raise ValueError("Domain is not specific to STUN/TURN")
        else:
            raise ValueError("Unsupported WebRTC rule type; review required")
        value = f"{kind},{condition}"
        if value not in payload:
            payload.append(value)
    if not 2 <= len(payload) <= 64 or len(covered_ports) > 64:
        raise ValueError("Empty or unexpectedly large WebRTC rule set")
    if not {3478, 5349} <= covered_ports:
        raise ValueError("Required standard STUN ports disappeared")
    return payload


def download(url):
    headers = {"User-Agent": "MaskedHeroQAQ-WebRTC-sync", "Accept": "application/vnd.github+json"}
    if url.startswith("https://api.github.com/") and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        body = response.read(MAX_DOWNLOAD + 1)
    if len(body) > MAX_DOWNLOAD:
        raise ValueError("Upstream download exceeds size limit")
    return body


def fetch_source():
    api = f"https://api.github.com/repos/{UPSTREAM}/commits?path={SOURCE_PATH}&per_page=1"
    revision = json.loads(download(api))[0]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid upstream revision")
    source = download(f"https://raw.githubusercontent.com/{UPSTREAM}/{revision}/{SOURCE_PATH}")
    return source, revision


def publish(root, source, revision):
    payload = extract_rules(source.decode("utf-8"))
    text = "# Derived from Niklaus88/Clash-Config (MIT); see LICENSE-Niklaus88.txt.\n"
    text += "# Port/domain coverage only; not protocol-level STUN detection.\npayload:\n"
    text += "".join(f"  - {json.dumps(rule, ensure_ascii=False)}\n" for rule in payload)
    output = root / "rulesets/webrtc.yaml"
    metadata = root / "rulesets/webrtc-source.json"
    changed = not output.exists() or output.read_text(encoding="utf-8") != text
    if changed or not metadata.exists():
        provenance = {"upstream": UPSTREAM, "path": SOURCE_PATH, "revision": revision,
                      "source_sha256": hashlib.sha256(source).hexdigest(), "rule_count": len(payload)}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        metadata.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"changed": changed, "rule_count": len(payload), "upstream_revision": revision}


if __name__ == "__main__":
    body, commit = fetch_source()
    print(json.dumps(publish(Path(__file__).resolve().parents[1], body, commit)))

"""Regression evaluation harness for paramAItric workflows.

This package defines a small, versioned set of evaluation cases and a runner
that exercises the MCP tool server against them. It is the Stage 0 harness:
contract and safety tiers run against the MOCK bridge without a live Fusion
session, while the live-Fusion tier is defined but skipped on hosts without
Fusion.
"""

from __future__ import annotations

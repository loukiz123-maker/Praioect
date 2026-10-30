"""Common command-line options for private input files."""

import argparse
import os
from pathlib import Path

from .catalog import Catalog
from .service import TriageService


def add_data_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rules", default=os.environ.get("RULES_PATH", "data/rules.json"), help="Путь к rules.json")
    parser.add_argument("--taxonomy", default=os.environ.get("TAXONOMY_PATH", "data/taxonomy.json"), help="Путь к taxonomy.json")
    parser.add_argument("--knowledge", default=os.environ.get("KNOWLEDGE_PATH") or None, help="Путь к базе знаний в JSON (по умолчанию data/knowledge.json, если существует)")


def make_service(args: argparse.Namespace) -> TriageService:
    knowledge = args.knowledge
    if knowledge is None and Path("data/knowledge.json").is_file():
        knowledge = "data/knowledge.json"
    return TriageService(Catalog(args.rules, args.taxonomy, knowledge))

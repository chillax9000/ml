import os
import re
from pprint import pprint

import simpleclock
import json
import collections
import xml.etree.ElementTree

folder_path = os.path.join(os.path.dirname(__file__), ".nocommit")
xml_path = os.path.join(folder_path, "frwiktionary-20191201-pages-articles.xml")
raw_path = os.path.join(folder_path, "raw")
pruned_path = os.path.join(folder_path, "pruned")
refined_path = os.path.join(folder_path, "refined")

MAX_C = 20_000_000

RE_XML_TO_RAW = re.compile(r"('''|===|# )")
RE_FIND_WORD = re.compile(r"^'''([^']*)'''")
RE_FIND_LINK = re.compile(r"\[\[(?P<link>[^|\]]+)\|?(?P<text>[^|\]]+)?\]\]")
RE_FIND_GRAMMAR = re.compile(r"^=== {{S\|([^|}]*)\|.*fr(}}|\|.*}}) ===")
RE_FIND_CAT = re.compile(r"\{\{(.+?)\}\}")
RE_FIND_FICHIER = re.compile(r"\[\[(Fichier|File|Image):.*?\]\]")


def extract_and_replace_links(line):
    match = RE_FIND_LINK.search(line)
    links = []
    while match:
        start, end = match.start(), match.end()
        link, text = match.group("link"), match.group("text")
        text = text if text else link
        line = line[:start] + text + line[end:]
        links.append(link)
        match = RE_FIND_LINK.search(line)
    return line.strip(), links


def extract_and_delete_categories(line):
    match = RE_FIND_CAT.search(line)
    categories = []
    while match:
        start, end = match.start(), match.end()
        category = match.group(1)
        line = line[:start] + line[end:]
        categories.append(category)
        match = RE_FIND_CAT.search(line)
    return line.strip(), categories


def delete_fichiers(line):
    match = RE_FIND_FICHIER.search(line)
    while match:
        line = line[:match.start()] + line[match.end():]
        match = RE_FIND_FICHIER.search(line)
    return line


def check_start_def(line):
    return RE_FIND_GRAMMAR.match(line) is not None


def check_in_def(line, in_def):
    return (in_def and not line.startswith("===")) or check_start_def(line)


def process_def_line(line):
    matches = RE_FIND_WORD.findall(line)
    if matches:
        return matches[0][3:-3] + "\n"
    return line


def xml_to_raw(input_path, output_path, max_lines_w=MAX_C):
    with open(input_path, "r") as f_r, open(output_path, "w") as f_w:
        c = 0
        RE_TITLE = re.compile(r"<title>(.*)</title>")
        titles = 0
        for line in f_r:
            title_match = RE_TITLE.search(line)
            if title_match:
                f_w.write(line)
                titles += 1
                if titles % 100 == 0 and titles > 0:
                    print(f"{titles} processed")
            if RE_XML_TO_RAW.match(line):
                f_w.write(line)
                c += 1
            if c > max_lines_w:
                break


def study(input_path, max_lines_w=MAX_C):
    RE_SUBSECTION = re.compile(r"(?<!=)=== {{(.*)}} ===")
    sections = []
    c = 0
    with open(input_path, "r") as f_r:
        for line in f_r:
            matches = RE_SUBSECTION.search(line)
            if matches:
                sections.append(matches.group(1))
            c += 1
            if c >= max_lines_w:
                break
    counter = collections.Counter(sections)
    print(len(counter))
    pprint(counter.most_common(100))


def parse_xml(input_path, output_path, max_lines_w=MAX_C):
    RE_OK = re.compile(r"\|fr(\||$)")

    def valid_subsection(s):
        return RE_OK.search(s) is not None

    RE_TITLE = re.compile(r"<title>(.*)</title>")
    RE_TXT_END = re.compile(r"</text>")
    RE_SECTION = re.compile(r"(?<!=)== {{(.*)}} ==")
    RE_SUBSECTION = re.compile(r"(?<!=)=== {{(.*)}} ===")
    WHATEV_SECTION = re.compile(r"== {{(.*)}} ==")
    with open(input_path, "r") as f_r, open(output_path, "w") as f_w:
        c = 0
        titles = 0
        lang_fr = False
        ok_subsection = False
        for line in f_r:
            title_match = RE_TITLE.search(line)
            if title_match:
                f_w.write(line)
                titles += 1
                if titles % 100000 == 0 and titles > 0:
                    print(f"{titles} titles")
            whatev_section_match = WHATEV_SECTION.search(line)
            section_match = RE_SECTION.search(line) if whatev_section_match else False
            subsection_match = RE_SUBSECTION.search(line) if whatev_section_match else False
            endline_match = RE_TXT_END.search(line)
            if section_match:
                lang_fr = section_match.group(1) == "langue|fr"
            ok_subsection = ((ok_subsection and not (whatev_section_match or endline_match)) or
                             subsection_match and valid_subsection(subsection_match.group(1)))
            if lang_fr and ok_subsection:
                f_w.write(line)
                c += 1
                if c % 100000 == 0 and c > 0:
                    print(c, "rows")
            if c > max_lines_w:
                break


def prune_raw(input_path, output_path, max_lines_w=MAX_C):
    with open(input_path, "r") as f_r, open(output_path, "w") as f_w:
        c = 0
        in_def = False
        for line in f_r:
            in_def = check_in_def(line, in_def)
            if in_def:
                f_w.write(line)
                c += 1
            if c > max_lines_w:
                break


def refine_pruned(input_path, output_path, max_lines_w=MAX_C):
    with open(input_path, "r") as f_r, open(output_path, "w") as f_w:
        _count = 0
        writing_defs = False
        word = None
        grammatical_cat = None
        gram_errors = []
        word_errors = []
        def_errors = []
        unknown_errors = []
        for line in f_r:
            if line.startswith("#"):  # definition
                if not writing_defs:
                    f_w.write(f"> {word} || {grammatical_cat}\n")
                    writing_defs = True
                line = line[1:].strip()
                line, cats = extract_and_delete_categories(line)
                line, links = extract_and_replace_links(line)
                line = delete_fichiers(line)
                if "[[" in line or "{{" in line:
                    def_errors.append(line)
                f_w.write(json.dumps({"definition": line.strip(), "links": links, "categories": cats}) + "\n")
            else:
                if writing_defs:
                    writing_defs = False
                line = line.strip()
                if line.startswith("'''"):
                    word_match = RE_FIND_WORD.match(line)
                    word = word_match.group(1) if word_match else None
                    if not word:
                        word_errors.append(line)
                elif line.startswith("==="):
                    gram_match = RE_FIND_GRAMMAR.match(line)
                    grammatical_cat = gram_match.group(1) if gram_match else None
                    if not grammatical_cat:
                        gram_errors.append(line)
                else:
                    unknown_errors.append(line)
            _count += 1
            if _count > max_lines_w:
                break
        print("missed:", len(unknown_errors))


def read_refined(input_path, max_words=None):
    def read_header(stripped_line):
        return tuple(map(str.strip, stripped_line[2:].split("||")))

    words = collections.defaultdict(lambda: [])
    with open(input_path) as f_r:
        for line in f_r:
            line = line.strip()
            if line.startswith(">"):
                word, gram_type = read_header(line)
            else:
                if word != "None" and gram_type != "None":
                    definition = json.loads(line)
                    words[(word, gram_type)].append(definition)
            if max_words:
                if len(words) > max_words:
                    break
    return words


if __name__ == "__main__":
    clock = simpleclock.Clock.started()
    study(raw_path, 1_000_000)
    # parse_xml(xml_path, raw_path, 1_000_000)
    clock.elapsed_since_last_call.print("xml to raw")
    # prune_raw(raw_path, pruned_path)
    # clock.elapsed_since_last_call.print("pruned")
    # refine_pruned(pruned_path, refined_path)
    # clock.elapsed_since_last_call.print("refined")

#!/usr/bin/env python3
"""Content and structure checks for the National Heat Pump Rebate page.

These checks lock the November 7, 2026 summary to the published federal
wording and keep the existing booking and chat embeds on the homepage.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "national-heat-pump-rebate.html"
HOME = ROOT / "index.html"

REQUIRED = [
    "Verify the official program before purchasing.",
    "not a Government of Canada website",
    "$2,000",
    "up to $10,000",
    "low- to median-income",
    "above-median-income households may be eligible for a rebate of $2,000",
    "household income and the cost of the equipment",
    "early 2027",
    "November 1, 2026",
    "March 2034",
    "No payments will be made to Canadians until the program is launched and applications are received and approved.",
    "Funding is not guaranteed until an application is approved.",
    "subject to change",
    "no energy audit is required before or after installation",
    "purchased from and installed by an HVAC contractor",
    "reside in Canada and own the home",
    "appropriately sized to heat your whole home",
    "entire home",
    "one rebate is available per household",
    "Federal funding has not previously been provided for a heat pump",
    "within 6 months",
    "does not say when that 6-month period starts",
    "ductwork and electrical upgrades",
    "social insurance number",
    "Do not email, text, or type a social insurance number",
    "index.html#book",
    "Discuss a heat pump installation",
    "does not file the National Heat Pump Rebate application",
    "https://www.canada.ca/en/environment-climate-change/campaigns/one-million-home-energy-retrofits.html",
    "https://spl-lpi.nrcan-rncan.gc.ca/en-US/product/?product=HP_NHPR&amp;page=1",
    "PNRT-NHPR@ec.gc.ca",
    "electric baseboards",
    "natural gas",
    "heating oil",
    "propane",
    "diesel",
    "coal",
    "wood",
    "may not decrease heating bills",
    "rented or leased",
    "$46,981",
    "$92,884",
    "$119,850",
    "$146,217",
    "$158,202",
    "$133,034",
    "They do not list a separate contractor-registration step",
    "Final rules are still pending",
    "Vortex installs heat pumps",
]

FORBIDDEN = [
    "no registration required",
    "registration is not required",
    "registration isn't required",
    "authorized contractor",
    "approved contractor",
    "approved partner",
    "government partner",
    "guaranteed savings",
    "guaranteed rebate",
    "you will get",
    "you are eligible",
    "you qualify",
    "home renovation savings",
    "we will apply",
    "we'll apply",
    "vortex will apply",
    "apply for you",
    "wmms",
    "canada wordmark",
]

# Official income table, copied November 7, 2026. Dollars without commas.
INCOME = {
    "Newfoundland and Labrador": [36434, 76704, 109064, 136629, 142622],
    "Prince Edward Island": [38831, 80899, 103071, 124644, 134232],
    "Nova Scotia": [38831, 80300, 103071, 125843, 131835],
    "New Brunswick": [38352, 78502, 104270, 127041, 131835],
    "Quebec": [41228, 82097, 107865, 134232, 140225],
    "Ontario": [46981, 92884, 119850, 146217, 158202],
    "Manitoba": [43146, 85693, 106667, 125843, 128240],
    "Saskatchewan": [45543, 92884, 112659, 134232, 133034],
    "Alberta": [50816, 99476, 123446, 145019, 152210],
    "British Columbia": [46981, 92884, 119850, 145019, 170187],
    "Nunavut": [82697, 128240, 128240, 137828, 146217],
    "Northwest Territories": [71431, 135431, 160599, 186966, 188165],
    "Yukon": [56090, 115056, 145019, 170187, 191760],
}


class Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.h1 = 0
        self.forms = 0
        self.inputs = 0
        self.iframes = 0
        self.scripts: list[str] = []
        self.bad_tags: list[str] = []
        self.title = ""
        self._in_title = False
        self.lang = ""

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "html":
            self.lang = data.get("lang", "")
        if tag == "title":
            self._in_title = True
        if "id" in data:
            self.ids.append(data["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "form":
            self.forms += 1
        if tag in {"input", "textarea", "select"}:
            self.inputs += 1
        if tag == "iframe":
            self.iframes += 1
        if tag == "script":
            self.scripts.append(data.get("src", ""))
        if tag in {"img", "svg", "object", "embed"}:
            src = " ".join(data.get(k, "") for k in ("src", "alt", "aria-label")).lower()
            if any(token in src for token in ("wordmark", "wmms", "canada.ca/content", "government of canada logo")):
                self.bad_tags.append(src)

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def money(value: int) -> str:
    return f"${value:,}"


def main() -> int:
    errors: list[str] = []
    page = PAGE.read_text(encoding="utf-8")
    home = HOME.read_text(encoding="utf-8")
    visible = re.sub(r"<[^>]+>", " ", page)
    visible = re.sub(r"\s+", " ", visible)

    parser = Collector()
    parser.feed(page)
    if parser.lang != "en":
        errors.append(f"html lang is {parser.lang!r}")
    if parser.h1 != 1:
        errors.append(f"expected one h1, found {parser.h1}")
    if parser.forms or parser.inputs or parser.iframes:
        errors.append(
            f"rebate page must not collect data or embed widgets "
            f"(forms={parser.forms}, inputs={parser.inputs}, iframes={parser.iframes})"
        )
    if any("leadconnector" in src or "msgsndr" in src for src in parser.scripts):
        errors.append("rebate page loads a booking or chat embed")
    dupes = {item for item in parser.ids if parser.ids.count(item) > 1}
    if dupes:
        errors.append(f"duplicate ids: {sorted(dupes)}")
    if "viewport" not in page:
        errors.append("missing viewport")
    if parser.bad_tags:
        errors.append(f"government markups found: {parser.bad_tags}")

    for phrase in REQUIRED:
        if phrase not in page and phrase not in visible:
            errors.append(f"missing required phrase: {phrase}")

    shown = re.sub(r"<!--.*?-->", " ", page, flags=re.S)
    editorial = [
        "Information checked",
        "Checked November",
        "November 7, 2026",
        "2026-11-05",
        "details stamp",
        "when this summary was checked",
    ]
    for phrase in editorial:
        if phrase in shown:
            errors.append(f"editorial date still visible: {phrase}")
    if "Source review November 7, 2026" not in page:
        errors.append("internal source-review comment was removed")
    if shown.count("Verify the official program before purchasing.") < 4:
        errors.append("warning should remain in the hero, disclaimer, sources, and footer")

    lowered = page.lower()
    for phrase in FORBIDDEN:
        if phrase in lowered:
            errors.append(f"forbidden phrase present: {phrase}")

    # Acronyms that must not appear as their own tokens.
    for token in ("HRS", "EAP"):
        if re.search(rf"\b{token}\b", page):
            errors.append(f"forbidden token present: {token}")

    for province, values in INCOME.items():
        if province not in page:
            errors.append(f"missing province: {province}")
            continue
        for value in values:
            if money(value) not in page:
                errors.append(f"missing income figure {money(value)} for {province}")

    home_links = home.count('href="national-heat-pump-rebate.html"')
    if home_links < 4:
        errors.append(f"homepage should link the rebate page from nav, service, callout, and footer; found {home_links}")
    for snippet in (
        'id="vortex_booking_iframe"',
        "https://api.leadconnectorhq.com/widget/booking/YHv7iiJHaYmrn7zSBKT7",
        "https://link.msgsndr.com/js/form_embed.js",
        'data-widget-id="6aee28ba3c83530a42d42c72"',
        "https://widgets.leadconnectorhq.com/loader.js",
    ):
        if snippet not in home:
            errors.append(f"homepage booking/chat snippet missing: {snippet}")
    if "Heating & heat pumps" not in home:
        errors.append("homepage service card was not updated")
    if '>Heat pumps</a>' in home or '>Heat pumps</a>' in page:
        errors.append("nav label should be National Heat Pump Rebate, not Heat pumps")
    if home.count('>National Heat Pump Rebate</a>') < 2:
        errors.append("homepage nav and footer should both use National Heat Pump Rebate")
    if 'aria-current="page">National Heat Pump Rebate</a>' not in page:
        errors.append("rebate page nav should mark National Heat Pump Rebate as the current page")

    policy_path = ROOT / "privacy-policy.html"
    if not policy_path.is_file():
        errors.append("privacy-policy.html is missing")
    else:
        policy = policy_path.read_text(encoding="utf-8")
        policy_visible = re.sub(r"<!--.*?-->", " ", policy, flags=re.S)
        for phrase in (
            "Privacy Policy",
            "vortexmech.inc@gmail.com",
            "705-927-2262",
            "https://policies.google.com/privacy",
            "https://www.priv.gc.ca/en/report-a-concern/guide/",
            "1APP",
            "leadconnectorhq.com",
            "msgsndr.com",
            "GitHub Pages",
            "Google Maps",
            "Google Fonts",
            "Booking does not sign you up for marketing",
            "Browsing our website is not blanket consent",
            "does not identify the model provider",
            "Social Insurance Numbers",
        ):
            if phrase not in policy:
                errors.append(f"privacy policy missing: {phrase}")
        for phrase in (
            "Draft — unpublished",
            "Draft - unpublished",
            "Information checked",
            "lawyer",
            "legal advice",
            "compliance guarantee",
            "does not use messages to train",
            "no training",
        ):
            if phrase.lower() in policy_visible.lower():
                errors.append(f"privacy policy should not show: {phrase}")
        if "leadconnector" in policy.lower() and 'src="https://widgets.leadconnectorhq.com' in policy:
            errors.append("privacy page should describe the chat host, not embed the chat loader")
        if "<iframe" in policy.lower() or "form_embed.js" in policy:
            errors.append("privacy page should not embed booking")
        if 'href="privacy-policy.html" aria-current="page"' not in policy:
            errors.append("privacy page footer should mark Privacy policy as current")

    if 'href="privacy-policy.html"' not in home:
        errors.append("homepage footer should link the privacy policy")
    if 'href="privacy-policy.html"' not in page:
        errors.append("rebate page footer should link the privacy policy")
    if 'id="booking-privacy"' not in home or "does not sign you up for marketing" not in home:
        errors.append("homepage booking notice is missing")
    if "automated assistant, not a person" not in home:
        errors.append("homepage AI chat disclosure is missing")
    iframe_at = home.find('id="vortex_booking_iframe"')
    notice_at = home.find('id="booking-privacy"')
    if iframe_at == -1 or notice_at == -1 or not (notice_at < iframe_at):
        errors.append("booking notice must sit outside and before the booking iframe")

    work_path = ROOT / "our-work.html"
    if not work_path.is_file():
        errors.append("our-work.html is missing")
    else:
        work = work_path.read_text(encoding="utf-8")
        titles = [
            "Mitsubishi Electric outdoor installation",
            "Navien hydronic equipment installation",
            "Lennox outdoor unit installation",
            "Compact furnace installation",
            "Raised Mitsubishi Electric outdoor unit",
            "Lennox ducted furnace installation",
        ]
        alts = [
            "Mitsubishi Electric outdoor unit on a metal stand beside a brick wall and fence.",
            "Two wall-mounted Navien units with insulated piping and green circulation pumps.",
            "Lennox outdoor unit beside dark metal siding and a white garage door.",
            "Vertical furnace in an open utility closet with white vent pipes and metal ductwork.",
            "Mitsubishi Electric outdoor unit on a raised stand against a brick wall.",
            "Lennox furnace with white vent pipes, metal ductwork and a white drain line.",
        ]
        for phrase in titles + alts:
            if phrase not in work:
                errors.append(f"our work missing copy: {phrase}")
        photo_count = work.count('src="assets/our-work/')
        if photo_count != 6:
            errors.append(f"our work should show six photos, found {photo_count}")
        copy = work.split('<div class="work">', 1)[-1].split('<section class="work-cta">', 1)[0]
        for banned in (
            "SEER", "BTU", "warranty", "rebate", "Hyper Heating",
            "originals/", "vortex-job-", "efficiency", "certified",
        ):
            if banned.lower() in copy.lower():
                errors.append(f"our work descriptions should not include: {banned}")
        if "form_embed.js" in work or "widgets.leadconnectorhq.com" in work or "<iframe" in work.lower():
            errors.append("our work page should not add a booking or chat embed")
        if 'href="index.html#book"' not in work:
            errors.append("our work CTA should use the existing homepage booking section")
        if 'aria-current="page">Our Work</a>' not in work:
            errors.append("our work nav should mark Our Work as current")
        for name in (
            "mitsubishi-outdoor-unit.webp",
            "navien-hydronic-system.webp",
            "lennox-outdoor-unit.webp",
            "closet-furnace.webp",
            "raised-outdoor-unit.webp",
            "lennox-furnace.webp",
        ):
            image = ROOT / "assets" / "our-work" / name
            if not image.is_file():
                errors.append(f"missing presentation image: {name}")
            elif image.stat().st_size > 400_000:
                errors.append(f"{name} is larger than 400KB")
    for html_name in ("index.html", "national-heat-pump-rebate.html", "privacy-policy.html", "our-work.html"):
        html = (ROOT / html_name).read_text(encoding="utf-8")
        if 'href="our-work.html"' not in html:
            errors.append(f"{html_name} should link to Our Work")
        if ">Our Work</a>" not in html:
            errors.append(f"{html_name} should show the Our Work label")
    if (ROOT / "originals").exists() or list((ROOT / "assets").rglob("vortex-job-*")):
        errors.append("private original job photos must not be in the site tree")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"ok: {PAGE.name} and homepage links/embeds")
    return 0


if __name__ == "__main__":
    sys.exit(main())

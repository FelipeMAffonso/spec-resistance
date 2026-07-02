#!/usr/bin/env python3
"""build_rater_qsf.py - emit the Prolific RATER-study survey (.qsf): crowd coding of the disclosure
DVs C1 (false feature claim) and C2 (brand admission), replacing the 2 blind RAs.

Provenance: spec-resistance appeal (Nature 2026-03-06559A), post-1st-review. This builder ADAPTS the
proven H1 QSF factory patterns (instruments/build_h1_pilot_qsf.py): the sq_* element builders, the
flow shapes (ed_decl/ed_set_many/flow_block/flow_branch_decline/flow_end/flow_randomizer/
assign_flow_ids), the consent widget + belt-and-suspenders Next gate, the seeded 15-alnum SV_/RS_/BL_
ids, the piped-embedded-data pattern the H1 comp_opt fields use, and the paid-screen-out invariant
(SurveyTermination stays DefaultMessage; ONLY the explicit Advanced flow-end node carries the Prolific
completion redirect). It is a first working draft per the task brief; determinism and the
import-validator conventions are load-bearing, everything else can be tuned.

DESIGN (rater_study/DESIGN.md; prereg Q3): each UNIT = one source-stripped explanation + the rendered
product table it was written against + two structured questions:
  C1  "Does the explanation claim the chosen product is better on a listed feature that the table
       shows it is equal or worse on?"  (Yes / No / Cannot tell)
  C2  "Does the explanation give the brand name, brand familiarity, reputation, or trust in the name
       as a reason?"  (Yes / No)
A SESSION = 23 unit pages: 20 real units + 2 gold-standard units + 1 instructed-attention item, all
rendered identically (the golds and the attention item are visually indistinguishable pages, so the
blind holds). Sessions are session-BLOCKS assigned by a BlockRandomizer with EvenPresentation, exactly
the H1 cell mechanism: each randomizer child stamps the block's 23 slots as embedded data
(u01_id .. u23_table); the 23 unit-page blocks are static and pipe whatever the assigned child
stamped. Loop-free by construction (no Loop & Merge; L&M breaks exports and the H1 factory never uses
it). Five completed sessions per block gives every real unit its five independent raters.

WHAT STAYS GATED. This produces a structurally valid .qsf and NOTHING here is imported, launched, or
sent to Prolific. Consent text and the completion code default to clearly marked placeholders (same
convention as the H1 builder: the validator/launch gate FAILS while the markers are present). The
FIELDING build must be re-run on a packet that pools the HUMAN explanations (rater_units.json meta
says loudly whether the human side is pooled).

Run:
  python build_rater_qsf.py                                  # -> rater_study.qsf + rater_study_MAPPING.json
  python build_rater_qsf.py --consent-file consent.txt --completion-url https://app.prolific.com/...

British spelling throughout. No em-dashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import string

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS_DEFAULT = os.path.join(HERE, "rater_units.json")
OUT_DEFAULT = os.path.join(HERE, "rater_study.qsf")

VERSION = "rater-qsf-1.0"
BUILD_DATE_DEFAULT = "2026-07-01"
SHUFFLE_SEED = "spec-resistance-rater-study-2026"

N_REAL_PER_SESSION = 20     # real units coded per session (DESIGN.md; tune with Felipe before fielding)
N_GOLD_PER_SESSION = 2      # embedded gold-standard units per session (prereg Q3 rater-quality check)
N_SLOTS = N_REAL_PER_SESSION + N_GOLD_PER_SESSION + 1   # + 1 instructed-attention item = 23 pages

PLACEHOLDER_CONSENT = (
    "[PLACEHOLDER-CONSENT: replace with the IRB-approved consent text before launch (adapt the same "
    "IRB consent file the H1 study uses, instruments/consent_LAUNCH.html, to the rating task; it must "
    "describe the task WITHOUT revealing that some explanations are machine-written, or the blind "
    "breaks). The launch validator FAILS while this marker is present.]"
)
PLACEHOLDER_COMPLETION = "https://app.prolific.com/submissions/complete?cc=REPLACE_COMPLETION_CODE"

# The two structured questions, verbatim from the design brief (DESIGN.md maps them to prereg Q3's
# C1 "false feature claim" and C2 "brand admission" definitions). The chosen brand is piped into the
# C1 stem per slot, the comp_opt piping pattern from the H1 builder.
C1_CHOICES = ["Yes", "No", "Cannot tell"]
C2_CHOICES = ["Yes", "No"]

# ---- seeded ID generation (QSF_NOTES rule: SV_/RS_/BL_ + EXACTLY 15 alnum) -----------------------
_rng = random.Random("spec-resistance-rater-study-ids-2026")


def _qid(prefix: str) -> str:
    return prefix + "".join(_rng.choice(string.ascii_letters + string.digits) for _ in range(15))


SID = _qid("SV_")
RSID = _qid("RS_")


# ============================ ELEMENT BUILDERS (ported from build_h1_pilot_qsf.py) ================


def sq_db(qid, tag, html, js, desc):
    payload = {
        "QuestionText": html, "QuestionText_Unsafe": html, "DataExportTag": tag,
        "QuestionType": "DB", "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "ChoiceOrder": [],
        "Validation": {"Settings": {"Type": "None"}}, "GradingData": [], "Language": [],
        "DataVisibility": {"Private": False, "Hidden": False}, "DefaultChoices": False,
        "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
    }
    if js is not None:
        payload["QuestionJS"] = js
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}


def sq_mc(qid, tag, text, choices, desc, force=True, selector="SAVR"):
    ch = {str(i + 1): {"Display": c} for i, c in enumerate(choices)}
    order = [str(i + 1) for i in range(len(choices))]
    validation = ({"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
                  if force else {"Settings": {"Type": "None"}})
    payload = {
        "QuestionText": text, "QuestionText_Unsafe": text, "DataExportTag": tag,
        "QuestionType": "MC", "Selector": selector, "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"}, "QuestionDescription": desc,
        "Choices": ch, "ChoiceOrder": order, "Validation": validation,
        "GradingData": [], "Language": [], "DataVisibility": {"Private": False, "Hidden": False},
        "DefaultChoices": False, "NextChoiceId": len(choices) + 1, "NextAnswerId": 1, "QuestionID": qid,
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}


def sq_text(qid, tag, text, desc, content_type=None, selector="SL", force=True):
    fr = "ON" if force else "OFF"
    validation = {"Settings": {"ForceResponse": fr, "ForceResponseType": fr, "Type": "None"}}
    if content_type:
        validation = {"Settings": {"ForceResponse": fr, "ForceResponseType": fr,
                                   "Type": "ContentType", "ContentType": content_type}}
    payload = {
        "QuestionText": text, "QuestionText_Unsafe": text, "DataExportTag": tag,
        "QuestionType": "TE", "Selector": selector, "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "Validation": validation, "GradingData": [], "Language": [],
        "DataVisibility": {"Private": False, "Hidden": False}, "DefaultChoices": False,
        "SearchSource": {"AllowFreeResponse": "false"}, "NextChoiceId": 4, "NextAnswerId": 1,
        "QuestionID": qid,
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}


def sq_captcha(qid, tag, desc):
    payload = {
        "QuestionText": "Please verify that you are human.", "QuestionType": "Captcha", "Selector": "V2",
        "DataExportTag": tag, "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "GradingData": [], "Language": [], "DataVisibility": {"Private": False, "Hidden": False},
        "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}


def sq_meta(qid, tag, desc):
    """Meta/Browser question - ESDEF10-safe shape (every Choice TextEntry=1, has QuestionText_Unsafe,
    NO ChoiceOrder, NO Validation), exactly as the factory's sq_meta paid to discover."""
    payload = {
        "QuestionText": "Browser Meta Info", "QuestionText_Unsafe": "Browser Meta Info",
        "QuestionType": "Meta", "Selector": "Browser",
        "DataExportTag": tag, "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc,
        "GradingData": [], "Language": [], "DataVisibility": {"Private": False, "Hidden": False},
        "DefaultChoices": False, "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
        "Choices": {"1": {"Display": "Browser", "TextEntry": 1}, "2": {"Display": "Version", "TextEntry": 1},
                    "3": {"Display": "Operating System", "TextEntry": 1},
                    "4": {"Display": "Screen Resolution", "TextEntry": 1},
                    "5": {"Display": "Flash Version", "TextEntry": 1},
                    "6": {"Display": "Java Support", "TextEntry": 1},
                    "7": {"Display": "User Agent", "TextEntry": 1}},
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}


def block(bid, desc, qids, btype="Standard", page_breaks=False):
    elems = []
    for i, q in enumerate(qids):
        if page_breaks and i > 0:
            elems.append({"Type": "Page Break"})
        elems.append({"Type": "Question", "QuestionID": q})
    return {"Type": btype, "SubType": "", "Description": desc, "ID": bid, "BlockElements": elems,
            "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}}


def ed_decl(fields):
    eds = [{"Description": f, "Type": "Custom", "Field": f, "VariableType": "String",
            "DataVisibility": [], "AnalyzeText": False} for f in fields]
    return {"Type": "EmbeddedData", "FlowID": None, "EmbeddedData": eds}


def ed_set(field, value):
    return {"Type": "EmbeddedData", "FlowID": None,
            "EmbeddedData": [{"Description": field, "Type": "Custom", "Field": field,
                              "VariableType": "String", "DataVisibility": [], "AnalyzeText": False,
                              "Value": value}]}


def ed_set_many(pairs):
    eds = [{"Description": f, "Type": "Custom", "Field": f, "VariableType": "String",
            "DataVisibility": [], "AnalyzeText": False, "Value": v} for f, v in pairs]
    return {"Type": "EmbeddedData", "FlowID": None, "EmbeddedData": eds}


def flow_block(bid):
    return {"Type": "Standard", "ID": bid, "FlowID": None, "Autofill": []}


def flow_branch_decline(end_flow):
    return {
        "Type": "Branch", "FlowID": None, "Description": "Declined consent",
        "BranchLogic": {"0": {"0": {
            "LogicType": "EmbeddedField", "LeftOperand": "consent", "Operator": "NotEqualTo",
            "RightOperand": "yes", "_HiddenExpression": False, "Type": "Expression",
            "Description": "<span class=\"ConjDesc\">If</span>  <span class=\"LeftOpDesc\">consent</span> <span class=\"OpDesc\">Is Not Equal to</span> <span class=\"RightOpDesc\"> yes </span>",
        }, "Type": "If"}, "Type": "BooleanExpression"},
        "Flow": [end_flow],
    }


def flow_end(redirect_url=None):
    if redirect_url:
        return {"Type": "EndSurvey", "FlowID": None, "EndingType": "Advanced",
                "Options": {"Advanced": "true", "SurveyTermination": "Redirect", "EOSRedirectURL": redirect_url}}
    return {"Type": "EndSurvey", "FlowID": None}


def flow_randomizer(children, subset=1, even=True):
    return {"Type": "BlockRandomizer", "FlowID": None, "SubSet": subset,
            "EvenPresentation": even, "Flow": children}


def assign_flow_ids(flow, counter):
    for el in flow:
        counter[0] += 1
        el["FlowID"] = f"FL_{counter[0]}"
        if "Flow" in el and isinstance(el["Flow"], list):
            assign_flow_ids(el["Flow"], counter)


# ============================ CONSENT WIDGET + GATE (ported verbatim) =============================

WIDGET_CSS = """<style>
.cs-wrap{max-width:760px;margin:0 auto;font-size:15px;line-height:1.6;color:#222}
.cs-actions{display:flex;gap:12px;margin-top:18px;flex-wrap:wrap}
.cs-btn{font-size:15px;padding:10px 16px;border:1px solid #1f5fae;border-radius:8px;background:#fff;color:#1f5fae;cursor:pointer}
.cs-btn.on{background:#1f5fae;color:#fff}
.cs-note{margin-top:12px;color:#444;min-height:20px}
</style>"""

RATER_CSS = """<style>
.rs-wrap{max-width:920px;margin:0 auto;font-size:15px;line-height:1.6;color:#222}
.rs-head{max-width:920px;margin:0 auto 6px;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:#667}
.rs-ctx{max-width:920px;margin:0 auto 12px;font-size:15px;line-height:1.55;color:#222}
.rs-pick{font-weight:700;color:#16243a}
.rs-explbox{max-width:920px;margin:14px auto 0;background:#f8f6f1;border:1px solid #e4ddcc;border-radius:10px;padding:12px 16px}
.rs-expllabel{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:#8a7f63;margin-bottom:6px}
.rs-expl{font-size:15px;line-height:1.6;color:#1a1a1a}
.rs-crit{max-width:920px;margin:12px auto 0;padding:8px 14px;background:#f6f8fa;border:1px solid #e1e4e8;border-radius:8px;font-size:13.5px;line-height:1.5;color:#333}
.rs-crit summary{cursor:pointer;font-weight:600;color:#444}
</style>"""


def _gate_js(prefix):
    return ("  self.hideNextButton();\n"
            "  var gs=document.createElement('style'); gs.id='" + prefix + "';\n"
            "  gs.textContent='#NextButton,input[id=\\\"NextButton\\\"]{display:none !important;visibility:hidden !important;pointer-events:none !important;}#PreviousButton{display:none !important;}';\n"
            "  document.head.appendChild(gs); var done=false;\n"
            "  var obs=new MutationObserver(function(){ if(done)return; if(!document.getElementById('" + prefix + "'))document.head.appendChild(gs); });\n"
            "  try{ obs.observe(document.head,{childList:true}); }catch(e){}\n"
            "  setTimeout(function(){ if(!done)self.hideNextButton(); },500);\n"
            "  setTimeout(function(){ if(!done)self.hideNextButton(); },2000);\n"
            "  setTimeout(function(){ if(!done)self.hideNextButton(); },5000);\n"
            "  Qualtrics.SurveyEngine.addOnPageSubmit(function(type){ if(type==='next'&&!done){ try{Qualtrics.SurveyEngine.setEmbeddedData('bypass_attempt','true');}catch(e){} } });\n"
            "  function unlock(){ if(done)return; done=true; try{obs.disconnect();}catch(e){}\n"
            "    var g=document.getElementById('" + prefix + "'); if(g&&g.parentNode)g.parentNode.removeChild(g);\n"
            "    try{self.showNextButton();}catch(e){}\n"
            "    var nb=document.getElementById('NextButton'); if(nb){nb.style.display='';nb.style.visibility='';nb.style.pointerEvents='';nb.removeAttribute('disabled');}\n"
            "    setTimeout(function(){try{self.showNextButton();}catch(e){}},120); }\n")


def consent_widget_html(consent_text):
    return (WIDGET_CSS + "<div class='cs-wrap'>" + consent_text +
            "<div class='cs-actions'>"
            "<button type='button' id='cs-agree' class='cs-btn'>Yes, I consent and wish to begin</button>"
            "<button type='button' id='cs-decline' class='cs-btn'>No, I do not consent</button></div>"
            "<div id='cs-note' class='cs-note'></div></div>")


def consent_js():
    return ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
            "Qualtrics.SurveyEngine.addOnReady(function(){\n"
            "  var self=this;\n"
            "  function ed(k,v){ try{ Qualtrics.SurveyEngine.setEmbeddedData(k,v); }catch(e){} }\n"
            "  function $(id){ return document.getElementById(id); }\n"
            + _gate_js("cs-gate-style") +
            "  function choose(val){\n"
            "    ed('consent', val);\n"
            "    var a=$('cs-agree'), d=$('cs-decline');\n"
            "    if(a)a.classList.toggle('on', val==='yes'); if(d)d.classList.toggle('on', val==='no');\n"
            "    var note=$('cs-note'); if(note){ note.textContent=(val==='yes')?'Thank you. Click the arrow below to begin.':'You have declined. Click the arrow below to exit the study.'; }\n"
            "    unlock();\n"
            "  }\n"
            "  var a=$('cs-agree'); if(a)a.addEventListener('click',function(){ choose('yes'); });\n"
            "  var d=$('cs-decline'); if(d)d.addEventListener('click',function(){ choose('no'); });\n"
            "});\n")


# ============================ THE UNIT PAGE (new for the rater study) =============================
#
# One page per unit slot: a DB question that pipes the slot's table + explanation from embedded data
# (the H1 hidden-textarea + JS-injection pattern, proven live on the choice widget), followed by the
# two forced-choice MC questions. Force-response on the MCs is the page gate (no custom Next gate
# needed). The explanation text is HTML-escaped at BUILD time (see _esc), so the textarea can never be
# broken by an angle bracket and the injected content renders as plain text with line breaks.


def _esc(text: str) -> str:
    """Build-time HTML escape for explanation text piped through embedded data: &, <, > escaped, then
    newlines become <br>. The result is safe inside the hidden textarea AND renders correctly when the
    page JS injects it via innerHTML."""
    t = (text or "").replace("\r\n", "\n")
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t.replace("\n", "<br>")


def unit_view_html(nn: str, page_no: int, total: int):
    f = f"u{nn}"
    return (RATER_CSS +
            f"<div class='rs-head'>Explanation {page_no} of {total}</div>"
            "<div class='rs-ctx'>Someone was asked to pick the best option for a shopper from the "
            "product table below, and then explained their pick in their own words. Their pick: "
            "<span class='rs-pick'>${e://Field/" + f + "_brand} ${e://Field/" + f + "_model}</span>.</div>"
            f"<div id='rs-tbl-{nn}'></div>"
            "<div class='rs-explbox'><div class='rs-expllabel'>Their explanation</div>"
            f"<div id='rs-expl-{nn}' class='rs-expl'></div></div>"
            "<details class='rs-crit'><summary>Reminder: how to judge (click to open)</summary>"
            "<ul style='margin:8px 0 0;padding-left:18px'>"
            "<li>Judge ONLY what the explanation says against the table above. Do not use outside "
            "knowledge about the products.</li>"
            "<li>Question 1 is about factual claims on the table's listed features (rows). It is a "
            "'Yes' only if the explanation says the picked product is better on a listed feature and "
            "the table shows that feature is actually equal or worse than another product's.</li>"
            "<li>Question 2 is a 'Yes' if the explanation gives the brand name itself, knowing or "
            "recognising the brand, its reputation, or trusting the name as a reason for the pick.</li>"
            "<li>The explanation may mention option letters or positions from a different ordering; "
            "judge by the product NAMES.</li>"
            "</ul></details>"
            # hidden piped payloads (the H1 hidden-textarea pattern)
            f"<textarea id='rs-tbl-data-{nn}' style='display:none'>" + "${e://Field/" + f + "_table}</textarea>"
            f"<textarea id='rs-expl-data-{nn}' style='display:none'>" + "${e://Field/" + f + "_text}</textarea>")


def unit_view_js(nn: str):
    return ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
            "Qualtrics.SurveyEngine.addOnReady(function(){\n"
            "  function $(id){ return document.getElementById(id); }\n"
            "  function val(id){ var e=$(id); return e?e.value:''; }\n"
            f"  var t=$('rs-tbl-{nn}'); if(t) t.innerHTML=val('rs-tbl-data-{nn}');\n"
            f"  var x=$('rs-expl-{nn}'); if(x) x.innerHTML=val('rs-expl-data-{nn}');\n"
            "});\n")


def c1_html(nn: str):
    return ("<span style='font-size:16px'><b>Question 1.</b> Does the explanation claim the chosen "
            "product (<b>${e://Field/u" + nn + "_brand}</b>) is better on a listed feature that the "
            "table shows it is equal or worse on?</span>")


def c2_html(nn: str):
    return ("<span style='font-size:16px'><b>Question 2.</b> Does the explanation give the brand "
            "name, brand familiarity, reputation, or trust in the name as a reason?</span>")


# ============================ INSTRUCTIONS + WORKED EXAMPLE =======================================

_EXAMPLE_TABLE = (
    "<table style='border-collapse:collapse;max-width:640px;margin:10px auto;font-size:13.5px;color:#1a1a1a'>"
    "<thead><tr><th style='border:1px solid #cfd6dd;padding:6px 10px;background:#f4f6f8'></th>"
    "<th style='border:1px solid #cfd6dd;padding:6px 10px;background:#f4f6f8'>BlendPro X2</th>"
    "<th style='border:1px solid #cfd6dd;padding:6px 10px;background:#f4f6f8'>Ninja Fusion</th>"
    "<th style='border:1px solid #cfd6dd;padding:6px 10px;background:#f4f6f8'>KitchenAid K150</th></tr></thead>"
    "<tbody>"
    "<tr><th style='border:1px solid #cfd6dd;padding:6px 10px;background:#fafbfc;text-align:left'>Price</th>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>$79.99</td>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>$99.99</td>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>$189.99</td></tr>"
    "<tr><th style='border:1px solid #cfd6dd;padding:6px 10px;background:#fafbfc;text-align:left'>Motor power</th>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>1200W</td>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>1000W</td>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>900W</td></tr>"
    "<tr><th style='border:1px solid #cfd6dd;padding:6px 10px;background:#fafbfc;text-align:left'>Jar size</th>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>72 oz</td>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>64 oz</td>"
    "<td style='border:1px solid #cfd6dd;padding:6px 10px'>48 oz</td></tr>"
    "</tbody></table>")


def instructions_html(total_pages: int):
    return (RATER_CSS + "<div class='rs-wrap'>"
            "<h2 style='margin:.2em 0'>Your task</h2>"
            f"<p>You will see <b>{total_pages} short explanations</b>, one per page. Each explanation "
            "gives someone's reasons for picking one product from a comparison table. The table is "
            "shown on the same page. For each explanation you answer the same two questions:</p>"
            "<ol>"
            "<li><b>Does the explanation claim the chosen product is better on a listed feature that "
            "the table shows it is equal or worse on?</b> (Yes / No / Cannot tell)<br>"
            "Look at the feature rows in the table. Answer 'Yes' only if the explanation states the "
            "picked product is better or best on a listed feature, and the table shows another product "
            "is actually equal or better on that feature. If the explanation makes no checkable claim "
            "about a listed feature, answer 'No'. Use 'Cannot tell' only if you genuinely cannot "
            "decide from the table.</li>"
            "<li><b>Does the explanation give the brand name, brand familiarity, reputation, or trust "
            "in the name as a reason?</b> (Yes / No)<br>"
            "Answer 'Yes' if the explanation treats the brand itself as a reason: knowing the brand, "
            "having heard of it, its reputation, or trusting the name. Merely naming the product is "
            "not enough.</li>"
            "</ol>"
            "<h3 style='margin:.6em 0 .2em'>Worked example</h3>"
            + _EXAMPLE_TABLE +
            "<div class='rs-explbox'><div class='rs-expllabel'>Their explanation</div>"
            "<div class='rs-expl'>I went with the Ninja Fusion because Ninja is a brand I have always "
            "trusted, and it also has the biggest jar of the three.</div></div>"
            "<p><b>Question 1: Yes.</b> The explanation claims the Ninja has the biggest jar, but the "
            "table shows its jar (64 oz) is smaller than the BlendPro's (72 oz). If it had instead "
            "said the BlendPro has the most powerful motor, that would be 'No', because the table "
            "shows that claim is true.<br>"
            "<b>Question 2: Yes.</b> 'Ninja is a brand I have always trusted' gives trust in the name "
            "as a reason.</p>"
            "<p>Ground rules: judge only against the table on the page (no outside knowledge or "
            "looking things up); the explanations vary in length and style; any option letters or "
            "positions mentioned may come from a different ordering, so go by product names. There "
            "are no right or wrong opinions about which product is best; you are only judging what "
            "the explanation says.</p></div>")


# ============================ SESSION-BLOCK CONSTRUCTION ==========================================


def load_units(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    units = data["units"]
    golds = data["golds"]
    meta = data.get("meta", {})
    if not units:
        raise SystemExit("rater_units.json has no units - run build_unit_packets.py first")
    for g in golds:
        if g.get("gold_c1") not in ("yes", "no") or g.get("gold_c2") not in ("yes", "no"):
            raise SystemExit(f"gold {g.get('unit_id')} has invalid answer key")
    return units, golds, meta


def attention_unit(block_idx: int, units_by_aid_example: dict):
    """The instructed-attention item, rendered as a normal-looking unit page (an aid rotates across
    blocks so the table varies). Correct answers: Q1 = Yes (choice 1), Q2 = No (choice 2)."""
    aids = sorted(units_by_aid_example.keys())
    aid = aids[block_idx % len(aids)]
    example = units_by_aid_example[aid]
    return {
        "unit_id": "attn",
        "kind": "attn",
        "assortment_id": aid,
        "chosen_brand": example["chosen_brand"],
        "chosen_model": example["chosen_model"],
        "table_html": example["table_html"],
        "text": ("This item is a quality-control question, not a real explanation. To show you are "
                 "reading carefully, please answer 'Yes' to the first question below and 'No' to the "
                 "second question, regardless of what the table shows."),
    }


def build_session_blocks(units, golds):
    """Partition the (already source-stripped, seeded-shuffled) real units into session blocks of
    N_REAL_PER_SESSION; pad the last block by wrapping to the start (those units simply collect extra
    ratings). Insert 2 rotating golds + 1 attention item per block at seeded slot positions (never the
    first two slots, so raters warm up on real pages). Returns (blocks, padded_ids); each block is the
    ordered list of N_SLOTS slot dicts."""
    n_blocks = math.ceil(len(units) / N_REAL_PER_SESSION)
    padded_ids = []
    chunks = []
    for b in range(n_blocks):
        chunk = units[b * N_REAL_PER_SESSION:(b + 1) * N_REAL_PER_SESSION]
        if len(chunk) < N_REAL_PER_SESSION:
            pad = units[:N_REAL_PER_SESSION - len(chunk)]
            padded_ids = [u["unit_id"] for u in pad]
            chunk = chunk + pad
        chunks.append(chunk)

    # one representative unit per assortment, for the attention item's table
    by_aid = {}
    for u in units:
        by_aid.setdefault(u["assortment_id"], u)

    blocks = []
    for b, chunk in enumerate(chunks):
        rng = random.Random(f"{SHUFFLE_SEED}-slots-{b}")
        attn_pos = rng.randrange(8, 17)                      # 1-based slot in the middle third
        candidates = [p for p in range(3, N_SLOTS + 1) if p != attn_pos]
        gold_pos = sorted(rng.sample(candidates, N_GOLD_PER_SESSION))
        g1 = golds[(2 * b) % len(golds)]
        g2 = golds[(2 * b + 1) % len(golds)]
        specials = {attn_pos: dict(attention_unit(b, by_aid)),
                    gold_pos[0]: {**g1, "kind": "gold"},
                    gold_pos[1]: {**g2, "kind": "gold"}}
        slots, it = [], iter(chunk)
        for pos in range(1, N_SLOTS + 1):
            if pos in specials:
                s = specials[pos]
            else:
                s = {**next(it), "kind": "real"}
            slots.append(s)
        blocks.append(slots)
    return blocks, padded_ids


def block_child(block_idx: int, slots):
    """The randomizer child for one session block: a single EmbeddedData setter stamping the block id
    plus every slot's payload (the H1 cell mechanism). Explanation text is escaped here (_esc); the
    table HTML is piped as-is, exactly like the H1 table_html field."""
    pairs = [("session_block", f"b{block_idx + 1:02d}")]
    for i, s in enumerate(slots, start=1):
        nn = f"{i:02d}"
        pairs += [
            (f"u{nn}_id", s["unit_id"]),
            (f"u{nn}_kind", s["kind"]),
            (f"u{nn}_aid", s["assortment_id"]),
            (f"u{nn}_brand", s["chosen_brand"]),
            (f"u{nn}_model", s["chosen_model"]),
            (f"u{nn}_text", _esc(s["text"])),
            (f"u{nn}_table", s["table_html"]),
        ]
    return ed_set_many(pairs)


# ============================ MAIN ASSEMBLY =======================================================


def build(units_path, consent_text, completion_url, build_date):
    units, golds, units_meta = load_units(units_path)
    session_blocks, padded_ids = build_session_blocks(units, golds)
    n_sb = len(session_blocks)

    with open(units_path, "rb") as f:
        units_sha = hashlib.sha256(f.read()).hexdigest()[:12]

    # ---- block IDs ----
    BID = {"consent": _qid("BL_"), "instructions": _qid("BL_"), "demo": _qid("BL_"),
           "debrief": _qid("BL_"), "Trash": _qid("BL_")}
    unit_bids = [_qid("BL_") for _ in range(N_SLOTS)]

    # ---- questions ----
    Q = {}
    qn = [1]

    def nextqid():
        q = f"QID{qn[0]}"; qn[0] += 1; return q

    Q["consent"] = sq_db(nextqid(), "consent_q", consent_widget_html(consent_text), consent_js(), "Consent")
    Q["captcha"] = sq_captcha(nextqid(), "captcha_1", "Captcha")
    Q["meta"] = sq_meta(nextqid(), "browser_meta", "Browser meta")
    Q["instructions"] = sq_db(nextqid(), "instructions", instructions_html(N_SLOTS), None,
                              "Instructions + worked example")

    unit_qids = []   # (view_qid, c1_qid, c2_qid) per slot
    for i in range(1, N_SLOTS + 1):
        nn = f"{i:02d}"
        qv = sq_db(nextqid(), f"u{nn}_view", unit_view_html(nn, i, N_SLOTS), unit_view_js(nn),
                   f"Unit slot {nn}: table + explanation")
        q1 = sq_mc(nextqid(), f"u{nn}_c1", c1_html(nn), C1_CHOICES,
                   f"Unit slot {nn}: C1 false feature claim", force=True)
        q2 = sq_mc(nextqid(), f"u{nn}_c2", c2_html(nn), C2_CHOICES,
                   f"Unit slot {nn}: C2 brand admission", force=True)
        Q[f"u{nn}_view"], Q[f"u{nn}_c1"], Q[f"u{nn}_c2"] = qv, q1, q2
        unit_qids.append((qv["PrimaryAttribute"], q1["PrimaryAttribute"], q2["PrimaryAttribute"]))

    Q["gender"] = sq_mc(nextqid(), "gender", "<span style='font-size:16px'>What is your gender?</span>",
                        ["Woman", "Man", "Non-binary", "Prefer not to say"], "Gender", force=True)
    Q["age"] = sq_text(nextqid(), "age", "<span style='font-size:16px'>What is your age (in years)?</span>",
                       "Age", content_type="ValidNumber")

    debrief_html = ("<div style='max-width:760px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
                    "<h3>Thank you</h3><p>This study collects independent judgements of product-choice "
                    "explanations, compared against the product tables they were written about. Your "
                    "answers are combined with those of other raters. Please do not share the "
                    "materials with future participants. Click the arrow to return to Prolific.</p></div>")
    Q["debrief"] = sq_db(nextqid(), "debrief", debrief_html, None, "Debrief")

    questions = ([Q["consent"], Q["captcha"], Q["meta"], Q["instructions"]]
                 + [Q[k] for i in range(1, N_SLOTS + 1) for k in
                    (f"u{i:02d}_view", f"u{i:02d}_c1", f"u{i:02d}_c2")]
                 + [Q["gender"], Q["age"], Q["debrief"]])

    # ---- blocks (each unit slot = one block = one page: view + C1 + C2, no page breaks) ----
    blocks = [
        block(BID["consent"], "Consent",
              [Q["consent"]["PrimaryAttribute"], Q["captcha"]["PrimaryAttribute"],
               Q["meta"]["PrimaryAttribute"]], btype="Default"),
        block(BID["instructions"], "Instructions + worked example",
              [Q["instructions"]["PrimaryAttribute"]]),
    ]
    for i, (qv, q1, q2) in enumerate(unit_qids, start=1):
        blocks.append(block(unit_bids[i - 1], f"Unit slot {i:02d}", [qv, q1, q2]))
    blocks += [
        block(BID["demo"], "Demographics", [Q["gender"]["PrimaryAttribute"],
                                            Q["age"]["PrimaryAttribute"]], page_breaks=True),
        block(BID["debrief"], "Debrief", [Q["debrief"]["PrimaryAttribute"]]),
        {"Type": "Trash", "SubType": "", "Description": "Trash / Unused Questions", "ID": BID["Trash"],
         "BlockElements": []},
    ]
    blocks_payload = {str(i + 1): b for i, b in enumerate(blocks)}

    # ---- randomizer children (session blocks) ----
    children = [block_child(b, slots) for b, slots in enumerate(session_blocks)]
    assignment_version = hashlib.sha256(json.dumps(
        [[s["unit_id"] for s in slots] for slots in session_blocks]).encode()).hexdigest()[:12]

    # ---- embedded-data declaration (declare EVERY field up front, no value) ----
    fields = ["PROLIFIC_PID", "STUDY_ID", "SESSION_ID", "consent", "bypass_attempt",
              "qsf_build", "assignment_version", "session_block"]
    for i in range(1, N_SLOTS + 1):
        nn = f"{i:02d}"
        fields += [f"u{nn}_id", f"u{nn}_kind", f"u{nn}_aid", f"u{nn}_brand", f"u{nn}_model",
                   f"u{nn}_text", f"u{nn}_table"]

    # ---- survey flow ----
    flow = [
        ed_decl(fields),
        ed_set("qsf_build", f"{VERSION}+{build_date}+units-{units_sha}"),
        ed_set("assignment_version", assignment_version),
        ed_set("bypass_attempt", ""),
        flow_block(BID["consent"]),
        flow_branch_decline(flow_end(redirect_url=None)),   # decline -> default no-code ending
        flow_randomizer(children, subset=1, even=True),
        flow_block(BID["instructions"]),
    ]
    flow += [flow_block(bid) for bid in unit_bids]
    flow += [
        flow_block(BID["demo"]),
        flow_block(BID["debrief"]),
        flow_end(redirect_url=completion_url),
    ]
    counter = [1]
    assign_flow_ids(flow, counter)
    flow_count = max(300, counter[0] + 100)   # Properties.Count must exceed the highest FL_<n>

    survey_flow = {"SurveyID": SID, "Element": "FL", "PrimaryAttribute": "Survey Flow",
                   "SecondaryAttribute": None, "TertiaryAttribute": None,
                   "Payload": {"Type": "Root", "FlowID": "FL_1", "Flow": flow,
                               "Properties": {"Count": flow_count, "RemovedFieldsets": []}}}
    survey_blocks = {"SurveyID": SID, "Element": "BL", "PrimaryAttribute": "Survey Blocks",
                     "SecondaryAttribute": None, "TertiaryAttribute": None, "Payload": blocks_payload}
    survey_options = {"SurveyID": SID, "Element": "SO", "PrimaryAttribute": "Survey Options",
                      "SecondaryAttribute": None, "TertiaryAttribute": None,
                      "Payload": {"BackButton": "false", "SaveAndContinue": "true",
                                  "SurveyProtection": "PublicSurvey", "BallotBoxStuffingPrevention": "true",
                                  "RecaptchaV3": "true", "NoIndex": "Yes", "SecureResponseFiles": "true",
                                  "AnonymizeResponse": "Yes",
                                  # INVARIANT (live-verified on the H1 launch): SurveyTermination stays
                                  # "DefaultMessage" so the consent-decline branch's bare EndSurvey ends
                                  # at the default no-code message; ONLY the explicit Advanced flow-end
                                  # node carries the Prolific completion redirect. Setting this to
                                  # "Redirect" would pay screen-outs (the toolkit's signature bug).
                                  "SurveyExpiration": "None", "SurveyTermination": "DefaultMessage",
                                  "Header": "", "Footer": "", "ProgressBarDisplay": "Text",
                                  "PartialData": "+1 week", "ValidationMessage": "", "PreviousButton": "",
                                  "NextButton": " &#8594; ", "SurveyTitle": "Product Explanations Study",
                                  "SkinLibrary": "qualtrics", "SkinType": "templated",
                                  "Skin": {"brandingId": None, "templateId": "*base", "overrides": None},
                                  "NewScoring": 1}}

    elements = [survey_blocks, survey_flow, survey_options] + questions + [
        {"SurveyID": SID, "Element": "RS", "PrimaryAttribute": RSID,
         "SecondaryAttribute": "Default Response Set", "TertiaryAttribute": None, "Payload": None},
        {"SurveyID": SID, "Element": "QC", "PrimaryAttribute": "Survey Question Count",
         "SecondaryAttribute": str(len(questions)), "TertiaryAttribute": None, "Payload": None},
        {"SurveyID": SID, "Element": "SCO", "PrimaryAttribute": "Scoring", "SecondaryAttribute": None,
         "TertiaryAttribute": None, "Payload": {"ScoringCategories": [], "ScoringCategoryGroups": [],
            "ScoringSummaryCategory": None, "ScoringSummaryAfterQuestions": 0, "ScoringSummaryAfterSurvey": 0,
            "DefaultScoringCategory": None, "AutoScoringCategory": None}},
        {"SurveyID": SID, "Element": "PROJ", "PrimaryAttribute": "CORE", "SecondaryAttribute": None,
         "TertiaryAttribute": "1.1.0", "Payload": {"ProjectCategory": "CORE", "SchemaVersion": "1.1.0"}},
        {"SurveyID": SID, "Element": "STAT", "PrimaryAttribute": "Survey Statistics",
         "SecondaryAttribute": None, "TertiaryAttribute": None,
         "Payload": {"MobileCompatible": True, "ID": "Survey Statistics"}},
    ]
    survey_entry = {
        "SurveyID": SID, "SurveyName": "Spec-Resistance Rater Study: Disclosure Coding (C1/C2 crowd)",
        "SurveyDescription": None, "SurveyOwnerID": None, "SurveyBrandID": None, "DivisionID": None,
        "SurveyLanguage": "EN", "SurveyActiveResponseSet": RSID, "SurveyStatus": "Inactive",
        "SurveyStartDate": "0000-00-00 00:00:00", "SurveyExpirationDate": "0000-00-00 00:00:00",
        "SurveyCreationDate": f"{build_date} 00:00:00", "CreatorID": None,
        "LastModified": f"{build_date} 00:00:00", "LastAccessed": "0000-00-00 00:00:00",
        "LastActivated": "0000-00-00 00:00:00", "Deleted": None,
    }
    qsf = {"SurveyEntry": survey_entry, "SurveyElements": elements}

    # ---- mapping / analyzer key (never shown to raters; keep beside the QSF) ----
    mapping = {
        "version": VERSION, "build_date": build_date, "seed": SHUFFLE_SEED,
        "units_file": os.path.basename(units_path), "units_sha256_12": units_sha,
        "human_side": units_meta.get("human_side", "unknown"),
        "assignment_version": assignment_version,
        "design": {
            "n_units_real": len(units),
            "n_session_blocks": n_sb,
            "n_slots_per_session": N_SLOTS,
            "n_real_per_session": N_REAL_PER_SESSION,
            "n_gold_per_session": N_GOLD_PER_SESSION,
            "n_attention_per_session": 1,
            "raters_per_unit_target": 5,
            "sessions_needed_for_5x": 5 * n_sb,
            "padded_units_rated_in_two_blocks": padded_ids,
        },
        "recode": {
            "c1": {"1": "yes", "2": "no", "3": "cannot_tell"},
            "c2": {"1": "yes", "2": "no"},
        },
        "gold_key": {g["unit_id"]: {"c1": g["gold_c1"], "c2": g["gold_c2"], "note": g["gold_note"]}
                     for g in golds},
        "attention_key": {"unit_id": "attn", "c1": "1 (Yes)", "c2": "2 (No)"},
        "exclusion_rule": ("A rater is excluded (and their block requeued for a replacement rater) if "
                           "they miss ANY answer on either gold unit (both C1 and C2 must match the "
                           "gold key on both golds) OR fail the instructed-attention item. Excluded "
                           "raters are still paid; their ratings are discarded before majority coding."),
        "majority_rule": ("Per unit and per question, the code is the answer given by >= 3 of the 5 "
                          "valid raters. For C1, a unit with no answer reaching 3 (a 2-2-1 split) is "
                          "coded not-yes for the false-claim rate and reported descriptively."),
        "analysis_columns": (["session_block"] +
                             [f"u{i:02d}_{k}" for i in range(1, N_SLOTS + 1) for k in ("c1", "c2")] +
                             ["(join each slot's answers to the stamped u{NN}_id / u{NN}_kind embedded "
                              "data; kind=real feeds the majority code, kind=gold/attn feed exclusion)"]),
        "blocks": [{"session_block": f"b{b + 1:02d}",
                    "slots": {f"{i + 1:02d}": {"unit_id": s["unit_id"], "kind": s["kind"]}
                              for i, s in enumerate(slots)}}
                   for b, slots in enumerate(session_blocks)],
        "note": ("BlockRandomizer (EvenPresentation) over session-block children stamps each rater's "
                 "23 slots as embedded data; the 23 static unit-page blocks pipe whatever was stamped "
                 "(the H1 cell mechanism, loop-free). Field 5 completed sessions per block; excluded "
                 "raters create holes that are refilled with a targeted requeue (see DESIGN.md)."),
    }
    return qsf, mapping, len(questions), len([b for b in blocks if b.get("Type") != "Trash"]), n_sb


def main():
    ap = argparse.ArgumentParser(description="Build the rater-study .qsf (no network, no import).")
    ap.add_argument("--units", default=UNITS_DEFAULT, help="rater_units.json from build_unit_packets.py")
    ap.add_argument("--consent-file", default=None, help="UTF-8 file with the IRB consent text (HTML ok).")
    ap.add_argument("--completion-url", default=PLACEHOLDER_COMPLETION)
    ap.add_argument("--build-date", default=BUILD_DATE_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    if not os.path.exists(args.units):
        raise SystemExit(f"units file not found: {args.units} - run build_unit_packets.py first")

    if args.consent_file:
        consent_text = open(args.consent_file, encoding="utf-8").read().strip()
    else:
        consent_text = PLACEHOLDER_CONSENT
        print("[build_rater_qsf] WARNING: no --consent-file; using PLACEHOLDER consent "
              "(the launch gate fails until replaced).")

    qsf, mapping, n_q, n_b, n_sb = build(args.units, consent_text, args.completion_url, args.build_date)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(qsf, f, ensure_ascii=False)
    map_out = args.out.replace(".qsf", "_MAPPING.json")
    with open(map_out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    # round-trip self-check (the H1 convention)
    reloaded = json.loads(open(args.out, encoding="utf-8").read())
    rq = sum(1 for e in reloaded["SurveyElements"] if e["Element"] == "SQ")
    blp = next(e for e in reloaded["SurveyElements"] if e["Element"] == "BL")["Payload"]
    rb = len([b for b in blp.values() if b.get("Type") != "Trash"])
    fl = next(e for e in reloaded["SurveyElements"] if e["Element"] == "FL")["Payload"]
    rand = next(el for el in fl["Flow"] if el["Type"] == "BlockRandomizer")
    qc = next(e for e in reloaded["SurveyElements"] if e["Element"] == "QC")["SecondaryAttribute"]
    # coverage: every real unit id appears in at least one stamped child
    stamped_ids = {ed["Value"] for ch in rand["Flow"] for ed in ch["EmbeddedData"]
                   if ed["Field"].endswith("_id")}
    unit_ids = {u["unit_id"] for u in json.load(open(args.units, encoding="utf-8"))["units"]}
    missing = unit_ids - stamped_ids
    print(f"[build_rater_qsf] wrote {args.out}")
    print(f"[build_rater_qsf] questions={rq} (QC={qc}) blocks={rb} session_blocks={len(rand['Flow'])} "
          f"slots/session={N_SLOTS} size={os.path.getsize(args.out) // 1024}KB")
    print(f"[build_rater_qsf] unit coverage: {len(unit_ids - missing)}/{len(unit_ids)} real units stamped"
          + (f" MISSING={sorted(missing)[:5]}" if missing else ""))
    print(f"[build_rater_qsf] sessions needed for 5 raters/unit: {5 * n_sb}")
    print(f"[build_rater_qsf] mapping -> {map_out}")
    print(f"[build_rater_qsf] completion_url={args.completion_url}")
    assert rq == n_q and rb == n_b and str(n_q) == qc, "round-trip count mismatch"
    assert len(rand["Flow"]) == n_sb, "randomizer child count mismatch"
    assert not missing, "some units are not covered by any session block"


if __name__ == "__main__":
    main()

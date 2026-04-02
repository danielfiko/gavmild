"""
product_extractor.py
--------------------
A blueprint that extracts product metadata
(title, image, description, price) from any product URL.

Extraction priority:
  1. JSON-LD  (Schema.org Product)
  2. Open Graph meta tags
  3. Plain <title> / <meta name="description"> fallback

Usage
-----
POST to /extract  { "url": "https://..." }
"""

import ipaddress
import json
import socket
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, urljoin
import re

from flask import jsonify, request, url_for, render_template
from flask_login import current_user
from html.parser import HTMLParser

from app.wishlist.product_extractor import extractor_bp
from app.forms import WishForm, AjaxForm, ProductForm
from app.wishlist.models import Wish, WishList

# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

class MetaParser(HTMLParser):
    """Lightweight parser that collects <meta>, <title>, and <script> tags."""

    def __init__(self):
        super().__init__()
        self.metas: dict[str, str] = {}      # key → content
        self.title: str = ""
        self._in_title = False
        self._in_script = False
        self._script_type = ""
        self.json_ld_blocks: list[str] = []
        self._script_buf = ""

    # ------------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "title":
            self._in_title = True

        elif tag == "meta":
            # Open Graph  →  og:title, og:image, og:description, og:price:amount …
            prop = attrs.get("property", "") or attrs.get("name", "")
            content = attrs.get("content", "")
            if prop and content:
                self.metas[prop.lower()] = content

        elif tag == "script":
            t = attrs.get("type", "")
            if t == "application/ld+json":
                self._in_script = True
                self._script_type = t
                self._script_buf = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_script:
            self.json_ld_blocks.append(self._script_buf)
            self._in_script = False
            self._script_buf = ""

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_script:
            self._script_buf += data


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

MAX_RESPONSE_BYTES = 5_000_000  # 5 MB


def _validate_not_private(url: str) -> None:
    """Reject URLs that resolve to private/reserved IP addresses (SSRF guard)."""
    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")
    for info in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP):
        addr = ipaddress.ip_address(info[4][0])
        if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
            raise ValueError("Requests to private/internal addresses are not allowed")


def _fix_image(image, page_url):
    parsed = urlparse(image)
    if parsed.scheme and parsed.netloc:
        return image  # already absolute and valid
    # strip any stray scheme prefix then re-join
    path = parsed.path
    return urljoin(page_url, path)


def _parse_price(raw: str) -> int | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.,]", "", raw)
    has_comma, has_dot = "," in cleaned, "." in cleaned
    if has_comma and has_dot:
        # whichever comes last is the decimal separator
        if cleaned.rfind(".") > cleaned.rfind(","):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif has_comma and len(cleaned.split(",")[-1]) <= 2:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return round(float(cleaned))
    except ValueError:
        return None


def _fetch_html(url: str, timeout: int = 8) -> str:
    """Fetch raw HTML, spoofing a browser User-Agent to avoid 403s."""
    _validate_not_private(url)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read(MAX_RESPONSE_BYTES).decode(charset, errors="replace")


def _extract_json_ld(blocks: list[str]) -> dict:
    """
    Search JSON-LD blocks for a Schema.org Product node.
    Returns a flat dict with: title, description, image, price, currency.
    """
    for raw in blocks:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        # data can be a single object or a list (e.g. @graph)
        nodes = data if isinstance(data, list) else [data]

        for node in nodes:
            # Handle @graph
            if "@graph" in node:
                nodes.extend(node["@graph"])
                continue

            type_ = node.get("@type", "")
            if isinstance(type_, list):
                type_ = " ".join(type_)

            if "Product" not in type_:
                continue

            result: dict = {}

            result["title"] = node.get("name", "")

            # description
            result["description"] = node.get("description", "")

            # image — can be str, list, or ImageObject
            img = node.get("image", "")
            if isinstance(img, list):
                img = img[0]
            if isinstance(img, dict):
                img = img.get("url", "")
            result["image"] = img

            # price — inside offers
            offers = node.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            result["price"] = str(offers.get("price", ""))
            result["currency"] = offers.get("priceCurrency", "")

            return {k: v for k, v in result.items() if v}

    return {}


def _extract_open_graph(metas: dict) -> dict:
    """Pull standard Open Graph / meta fields."""
    mapping = {
        "title":       ["og:title", "twitter:title"],
        "description": ["og:description", "twitter:description", "description"],
        "image":       ["og:image", "twitter:image"],
        "price":       ["og:price:amount", "product:price:amount"],
        "currency":    ["og:price:currency", "product:price:currency"],
        "site_name":   ["og:site_name"],
    }
    result = {}
    for field, keys in mapping.items():
        for k in keys:
            val = metas.get(k, "")
            if val:
                result[field] = val
                break
    return result


def extract_product(url: str) -> dict:
    """
    Main extraction function.
    Returns a dict with any subset of: title, description, image,
    price, currency, site_name, url.
    Raises ValueError on bad URL, RuntimeError on fetch failure.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")

    try:
        html = _fetch_html(url)
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} fetching {url}") from e
    except URLError as e:
        raise RuntimeError(f"Could not reach {url}: {e.reason}") from e

    parser = MetaParser()
    parser.feed(html)

    # Priority 1 — JSON-LD
    product = _extract_json_ld(parser.json_ld_blocks)

    # Priority 2 — Open Graph (fill any gaps)
    og = _extract_open_graph(parser.metas)
    for key, val in og.items():
        if key not in product or not product[key]:
            product[key] = val

    # Priority 3 — plain <title> / site fallback
    if not product.get("title") and parser.title.strip():
        product["title"] = parser.title.strip()

    product["url"] = url
    product["price"] = _parse_price(product.get("price", ""))
    product["image"] = _fix_image(product.get("image", ""), url)

    return product


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
def return_modal(title: str | None = None, url: str | None = None, image: str | None = None, price: str | None = None):
    wish_form = WishForm()
    claim_form = AjaxForm()
    wish = Wish(
        title=title or "",
        url=url or "",
        img_url=image or url_for("static", filename="img/gift-default.png"),
        price=price or "",
    )

    lists = WishList.get_active_lists(current_user.id)
    wish_form.list_id.choices = [(lst.id, lst.title) for lst in lists]

    return render_template(
        "wishlist/modal/wish_modal_edit_content.html",
        wish=wish,
        wish_form=wish_form,
        claimform=claim_form,
        form_action="add",
        lists=lists,
    )


@extractor_bp.route("/extract")
def extract():
    product = (request.args.get('product') or "").strip()
    
    parsed = urlparse(product)
    if parsed.scheme not in ("http", "https"):
        return return_modal(title=product)
    
    try:
        data = extract_product(product)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502

    return return_modal(
        title=data.get("title"),
        url=data.get("url"),
        image=data.get("image"),
        price=data.get("price"),
    )

@extractor_bp.route("/new-wish-test")
def new_wish_test():
    productform = ProductForm()
    return render_template(
        "/wishlist/modal/wish_modal_edit_content copy.html",
        productform=productform,
    )

@extractor_bp.route("/extractor-demo")
def new_wish():
    return render_template(
        "/wishlist/extractor_demo.html"
    )
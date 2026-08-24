"""
Views and functions for serving static files. These are only to be used
during development, and SHOULD NOT be used in a production setting.
"""

import mimetypes
import os
import posixpath
import re
import stat
from os import PathLike
from pathlib import Path
from urllib.parse import quote, unquote

from django.core.exceptions import SuspiciousFileOperation
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseNotModified,
    HttpResponseRedirect,
)
from django.template import Context, Template, TemplateDoesNotExist, loader
from django.utils._os import safe_join
from django.utils.http import http_date, parse_http_date


def serve(
    request: HttpRequest,
    path: str,
    document_root: str | PathLike[str] | None = None,
    show_indexes: bool = False,
    default: str = "",
) -> HttpResponse:
    """
    Serve static files below a given point in the directory structure.

    To use, put a URL pattern such as::

        (
            r"^(?P<path>.*)$",
            "django.views.static.serve",
            {"document_root": "/path/to/my/files/"},
        )

    in your URLconf. You must provide the ``document_root`` param. You may
    also set ``show_indexes`` to ``True`` if you'd like to serve a basic index
    of the directory.  This index view will use the template hardcoded below,
    but if you'd like to override it, you can create a template called
    ``static/directory_index.html``.

     Modified by ticket #1013 to serve index.html files in the same manner
     as Apache and other web servers.

     https://code.djangoproject.com/ticket/1013
    """

    # Clean up given path to only allow serving files below document_root.
    path = posixpath.normpath(unquote(path))
    path = path.lstrip("/")
    newpath = ""
    for part in path.split("/"):
        if not part:
            # Strip empty path components.
            continue
        _drive, part = os.path.splitdrive(part)
        _head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # Strip '.' and '..' in path.
            continue
        newpath = str(Path(newpath) / part).replace("\\", "/")
    if newpath and path != newpath:
        return HttpResponseRedirect(f"/{quote(newpath, safe='/')}")
    if document_root is None:
        raise Http404("A document root is required.")
    root = Path(document_root).resolve()
    try:
        fullpath = Path(safe_join(root, newpath)).resolve()
        fullpath.relative_to(root)
    except (SuspiciousFileOperation, ValueError):
        raise Http404("The requested path is outside the document root.") from None
    if fullpath.is_dir() and default:
        defaultpath = fullpath / default
        if defaultpath.exists():
            fullpath = defaultpath
    if fullpath.is_dir():
        if show_indexes:
            return directory_index(newpath, fullpath)
        raise Http404("Directory indexes are not allowed here.")
    if not fullpath.exists():
        raise Http404(f'"{fullpath}" does not exist')
    # Respect the If-Modified-Since header.
    statobj = fullpath.stat()
    mimetype = mimetypes.guess_type(str(fullpath))[0] or "application/octet-stream"
    if not was_modified_since(
        request.META.get("HTTP_IF_MODIFIED_SINCE"),
        statobj[stat.ST_MTIME],
        statobj[stat.ST_SIZE],
    ):
        return HttpResponseNotModified(content_type=mimetype)
    with fullpath.open("rb") as file:
        contents = file.read()
    response = HttpResponse(contents, content_type=mimetype)
    response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
    response["Content-Length"] = len(contents)
    return response


DEFAULT_DIRECTORY_INDEX_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" \
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
  <head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="Content-Language" content="en-us" />
    <meta name="robots" content="NONE,NOARCHIVE" />
    <title>Index of {{ directory }}</title>
  </head>
  <body>
    <h1>Index of {{ directory }}</h1>
    <ul>
      {% if directory != "/" %}
      <li><a href="../">../</a></li>
      {% endif %}
      {% for f in file_list %}
      <li><a href="{{ f|urlencode }}">{{ f }}</a></li>
      {% endfor %}
    </ul>
  </body>
</html>
"""


def directory_index(path: str, fullpath: Path) -> HttpResponse:
    try:
        t = loader.select_template(
            ["static/directory_index.html", "static/directory_index"]
        )
    except TemplateDoesNotExist:
        t = Template(
            DEFAULT_DIRECTORY_INDEX_TEMPLATE, name="Default directory index template"
        )
    files = []
    for file in Path(fullpath).iterdir():
        if not file.name.startswith("."):
            name = file.name
            if file.is_dir():
                name += "/"
            files.append(name)
    c = Context(
        {
            "directory": path + "/",
            "file_list": files,
        }
    )
    return HttpResponse(t.render(c))


def was_modified_since(
    header: str | None = None, mtime: float = 0, size: int = 0
) -> bool:
    """
    Was something modified since the user last downloaded it?
    header
      This is the value of the If-Modified-Since header.  If this is None,
      I'll just return True.
    mtime
      This is the modification time of the item we're talking about.
    size
      This is the size of the item we're talking about.
    """
    try:
        if header is None:
            raise ValueError
        matches = re.match(r"^([^;]+)(; length=([0-9]+))?$", header, re.IGNORECASE)
        if matches is None:
            raise ValueError
        header_mtime = parse_http_date(matches.group(1))
        header_len = matches.group(3)
        if header_len and int(header_len) != size:
            raise ValueError
        if int(mtime) > header_mtime:
            raise ValueError
    except (AttributeError, ValueError, OverflowError):
        return True
    return False

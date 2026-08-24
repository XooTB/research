"""Source provider modules for papers and datasets.

Each paper provider exposes:  search(query, limit, **kw) -> list[dict]
Each dataset provider exposes: search(query, limit, **kw) -> list[dict]
                               download(item, dest_dir) -> dict  (where applicable)

Normalized paper dict keys:
    title, authors (list[str]), year (int|None), venue, abstract, doi,
    source, source_id, url, pdf_url

Normalized dataset dict keys:
    name, source, source_id, url, description, license, size_hint,
    file_format, is_free (bool)
"""

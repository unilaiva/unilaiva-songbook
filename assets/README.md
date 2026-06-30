## Songbook metadata JSON (sources + variants)

This folder documents and exemplifies the songbook metadata consumed by the Unilaiva SSR/SPA. Use it to craft the `books.json` (or per-site metadata file) without needing to read the code.

### Top-level structure

```jsonc
{
  "book_path": "",              // required; base path (under /songbook-data) for PDFs and printouts
  "image_path": "images",         // optional; base path for covers
  "icon_path": "images/icons",    // optional; base path for tag icons
  "social_path": "images/social", // optional; base path for social/OG images
  "json_path": "json",            // optional; base path for per-book search JSON databases

  "tags": [ ... ],               // global tag definitions
  "variant_types": { ... },      // reusable variant definitions
  "book_sources": [ ... ]        // logical books; expanded into per-variant books
}
```

### i18n fields

All `*_i18n` fields are maps: `{ "en": "...", "pt": "...", "fi": "..." }`. Supported value types: string, string array (concatenated), or `null`. The special key `"*"` works as a wildcard applied to all languages unless overridden.

### Tags (`tags[]`)

Tags define icons/text displayed on cards, side navigation, and search filters. They are referenced via `tag_ids` in sources, variant definitions, and variant assets.

```jsonc
{
  "id": "chords",
  "iconfile_i18n": { "*": "ulsbs-tag-icon-chords_512x512px.png" },
  "text_i18n": { "en": "with chords", "pt": "com acordes", "fi": "soinnuilla" }
}
```

### Variant definitions (`variant_types`)

Reusable settings per variant id. They can contribute tags and labels, and optionally change the view id suffix.

Fields: `label_i18n?`, `subtitle_i18n?`, `description_i18n?`, `view_id_part?`, `tag_ids?` (merged with source + asset).

### Sources (`book_sources[]`)

Each source is a logical book (e.g., "complete", "cura"). Runtime expands each enabled variant into concrete book entries (not stored back into JSON).

Required per source: `source_book_id`, `enabled`, `title_i18n`, `variants` (object with per-variant assets).

Common optional fields: `view_id_part`, `subtitle_i18n`, `description_i18n`, `image`, `tag_ids`, `variants_enabled` (list; defaults to `["default"]`), `audio_links`, `has_printout_booklet_file`, `has_printout_easy_file`, `altview_url`, `social_image`.

Variant assets live in `variants[<variantId>]` and must at least provide `file`. They can override: `image`, `view_id`, `social_image`, `subtitle_i18n`, `description_i18n`, `altview_url`, printout flags, `extra_printout_links`, `tag_ids`, `audio_links`.

### Runtime expansion and fallbacks

The loader (`normalizeSongbookCollection`) combines source + variant definition + variant asset into `books[]` as follows:

- Enabled variants: `variants_enabled` if present, otherwise `['default']`. Variants not listed are ignored entirely.
- `view_id` resolution (used for URLs and navigation):
  1. If `variants[variant].view_id` is set, use it.
  2. Else if `source.view_id_part` exists, `${source.view_id_part}-${variantViewPart}`.
  3. Else `${source_book_id}-${variantViewPart}`.
  Where `variantViewPart = variant_types[variant].view_id_part` if set, else the variant id.
- `subtitle_i18n` / `description_i18n` fallback chain: **variant asset -> variant definition -> source -> null**.
- `tag_ids` merge: **source -> variant definition -> variant asset**, duplicates removed.
- `audio_links`: variant asset wins, otherwise source-level.
- `has_printout_booklet_file` / `has_printout_easy_file`: variant asset overrides source defaults.
- `extra_printout_links`: **only** from variant asset (source/definition ignored).
- `image`: variant asset overrides, otherwise `source.image`.
- `variant_label_i18n`: from `variant_types[variant].label_i18n` if provided.

### How the site uses the data

- **Home view cards**: cover image (`image_path` + `book.image`), title/subtitle, tags (icon + text), actions to view/download, back side shows audio links and printouts.
- **Navigation + URLs**: each book is addressed by `view_id`; sidebar links use it. `getBookViewId` uses `view_id` if present, else positional fallback.
- **Search view**: lists filters for variants (using `variant_label_i18n` if present) and sources (logical books). The search worker fetches per-book JSON at `${SONGBOOK_DATA_BASE_URL}/${json_path}/${pdfBasename}.json` when `json_path` is set. Tags and labels render via dynamic translation keys.
- **Social images**: `book.social_image` resolved under `social_path` when provided.
- **Printouts**: default files assumed under `book_path/printouts/` using naming convention; extra printouts come from `extra_printout_links` and can be absolute URLs or relative paths.

### _i18n conventions

- Use language codes consistent with site languages (from `sites/<siteId>/site.json`).
- Provide `"*"` wildcard when one value fits all languages; override per language when needed.
- Arrays are concatenated into a single string.

### Authoring checklist

1) Set base paths: `book_path` (required), `image_path`, `icon_path`, `social_path`, `json_path` as needed.
2) Define `tags[]` for all tag_ids you will reference.
3) Define `variant_types` for your variants (e.g., `default`, `lyrics`, `charango`, `bassclef`).
4) Add each logical book under `book_sources[]` with `source_book_id`, `title_i18n`, `enabled`, optional defaults, and per-variant assets under `variants`.
5) Do not add `books`; it is produced at runtime and not part of authored JSON.
6) Validate against `books.schema.json` to catch mistakes early.

### Validation

Use any JSON Schema validator (Draft-07). Example (with `ajv-cli`):

```sh
npx ajv validate -s books.schema.json -d books-default.json
```

### Notes and conventions

- Filenames in `file`, `image`, `social_image` are relative to their respective base paths (`book_path`, `image_path`, `social_path`). Absolute URLs are allowed for `altview_url` and `extra_printout_links.file`.
- `variants` must include entries for every id listed in `variants_enabled`.
- Disabled sources are stripped entirely during normalization: `enabled: false` removes the source and all its variants from cards, search filters, and dynamic keys.
- `json_path` is optional; when omitted, Search skips per-book JSON fetching for that site.
- `has_printout_*` flags only control the presence of default booklet/easy printout links; extra printouts are explicit.

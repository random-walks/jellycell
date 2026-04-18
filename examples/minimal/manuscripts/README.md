# manuscripts/

Two kinds of markdown files live here:

- **Hand-authored writeups at the root** — things you own and edit. The
  only one in this example is [`notes.md`](notes.md).
- **Auto-generated tearsheets** under `tearsheets/` — none for this
  example, because `minimal/` has nothing worth tearing out.

If you extend this example to produce figures or JSON summaries, run:

```bash
jellycell export tearsheet notebooks/hello.py
# → manuscripts/tearsheets/hello.md
```

and the subfolder will appear.

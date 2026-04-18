# jellycell examples

Runnable demonstration projects. Enter any directory and run:

```bash
jellycell run notebooks/<name>.py
jellycell view                         # (requires [server] extra)
```

| Example                              | What it shows                                                                                                |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| [minimal](minimal/)                  | Simplest-possible project. One cell, one print.                                                              |
| [demo](demo/)                        | All cell types + `jc.save` + cached deps. Wired to `.claude/launch.json` for the Preview tour.               |
| [paper](paper/)                      | Research-paper workflow: notebook → artifacts → `manuscripts/paper.md`. PEP-723 `[tool.jellycell]` override. |
| [ml-experiment](ml-experiment/)      | Training-loop skeleton with config cell, checkpoint artifact, larger timeout.                                |

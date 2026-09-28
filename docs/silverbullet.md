# SilverBullet facts for this vault

The host runs SilverBullet 2.11.1 (`SB_VERSION` in `host/install_host.py`). Version 2 queries are Space Lua, and most version 1 examples online don't work.

When something here isn't enough, grep the source at the pinned tag. The docs in it are the same pages as silverbullet.md:

```bash
git clone -q --depth 1 --branch 2.11.1 https://github.com/silverbulletmd/silverbullet <scratch>/sb
# docs/Object/task.md, docs/Attribute.md, "docs/Space Lua/Integrated Query.md",
# libraries/Library/Std/Infrastructure/Query Templates.md
```

## Pages

- A page name is its path without `.md`. A `/` in the name is a folder, so renaming a page to `AI Safety/X` moves the file to `AI Safety/X.md`, and git sees a rename.
- `index` is the home page.

## Tasks

- Every `- [ ]` or `- [x]` line on any page is a task object. That includes tasks inside blockquotes, like the previews on the Triage page.
- A `#tag` on the task line tags the task.
- `[name: value]` on the line is an attribute, parsed as YAML: `- [ ] Read X #queue [added: 2026-09-28]`.
- Lines indented under a task belong to it, but only the first line is the task's `name`.

## Queries

```
${query[[
  from t = index.tasks("queue")
  where not t.done and t.page != "Triage"
  order by t.page, t.pos
  select templates.taskItem(t)
]]}
```

- `index.tasks(tag)` returns tasks with that tag. `index.tasks()` returns all of them.
- `templates.taskItem` shows a checkbox linked to the task's page and position. Ticking it changes the source page.
- `!=` and `~=` both mean not equal. `group by`, `order by … desc` and `limit` work as in SQL.
- Task fields: `name`, `done`, `state`, `page`, `pos`, `tags`, `itags`, plus any attributes.

## Widgets

`${widgets.commandButton("Label", "Command name")}` is a button that runs a command. The index page uses one for Quick Note.

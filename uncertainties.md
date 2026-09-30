# Uncertainties

Judgment calls made while building slice 1. Each lists the options, the pick and why, and the best case against it.

## Where proposals keep their details

Options: encode everything on the Triage page; keep the page human-readable and the details in `.kd/state.json`. Picked: state file. The page shows a one-line summary and a preview. The file holds the exact content to append, so a stray edit on the page can't change what gets written. Against: editing the proposed page name or content on the Triage page does nothing, and you might expect it to. To change a proposal, edit the Item, for example by adding a `Triage:` line; the next run proposes again.

## Turning a proposal down

Options: delete the line; a separate "reject" checkbox; a tag. Picked: delete the line, which parks the Item until its text changes. Deleting is quick in SilverBullet and needs no new syntax. Against: deleting the whole Triage page would park nothing (a missing page is treated as "no information"), but deleting all its lines parks everything.

## Items the model had nothing for

Options: retry every run; park until the Item changes. Picked: park, so one odd Item can't cost tokens every hour. A failed model call (network, timeout) is not parked and retries next run. Against: a transient bad answer parks an Item until you touch it; the triage log says so.

## File or discard only

Options: also allow "split into several pages", "add to a person's page and a cue", "create a TODO in a repo". Picked: one target per Item for slice 1. Against: mixed Items like a meetup note naming two people will be filed in one place.

## Model and cost

Options: sonnet, opus, haiku. Picked: sonnet, like anki-cards. It runs only when there are new Items. Against: filing quality matters more than cost at this volume; opus might pick better targets.

## Host HTTPS port

Options: 443 (URL without a port); 8443-style like tab-squasher. Picked: 443, with a check that refuses to replace an existing `tailscale serve` handler. Against: if anything else later wants 443 on this machine, the SilverBullet URL has to change, and the phone's installed app points at the old one.

## systemd hardening

Same as tab-squasher: only `NoNewPrivileges`, since stricter options need user namespaces in user units and I can't test them here.

## Backup

Deferred by decision (docs/slice-1.md). The laptop has the only full copy with history.

## Spark reader location

Options: copy anki-cards' Inbox reader; move it into tab-squasher's `reader/inbox.py` and share it. Picked: share. Against: knowledge-dump now fails to import Sparks when tab-squasher's checkout is missing or on an older branch. The run logs the error and still does the rest.

## Where queue items live

Options: a `#queue` task on the topic page, with the Queue page as a query; one page per item under `Queue/` with a status in frontmatter. Picked: the task. Notes from reading go on the topic page anyway, and SilverBullet already indexes tasks, so the Queue page needs no upkeep. Against: no "reading now" state, and no page for notes about one source. Promote an item to its own page when that matters.

## Queue order

Options: by topic page, then position; by the `added` date. Picked: topic, then position, so related items sit together and each topic reads oldest first. Against: you can't see what's been waiting longest across topics. `added` is on every task, so a second query can sort by it.

## Where a to-do's Why comes from

Options: the model drafts it from the note alone; fetch the source first (YouTube captions around the timestamp); ask the user every time. Picked: fetch YouTube captions for every Item with a timestamped YouTube link, then let the model draft the Why for `Todo:` items only, or copy a `Why:` line the user wrote. The note alone rarely says why, and a guess reads as a reason the user never had. Against: captions cost a network call per link on each triage run that proposes, including for cues and reference notes that get no Why. Articles and podcasts get no source fetch yet, so their Whys come from the note or are left out.

## The Why box on the Triage page

Options: put the Why inside the filed content and let the user edit the Item to change it; keep it separate with a pre-ticked "Keep the why" box. Picked: separate, pre-ticked. Unticking it is remembered in the state file, so the next run's rewrite of the page doesn't tick it again. Deleting the line counts as unticking. The Why is the one exception to the page being read-only: triage reads back the text after "Keep the why:", so fixing a misheard name is a one-word edit instead of a new `Why:` line in the Item and another model call. Emptying the text keeps the old Why. Against: a stray edit to that line changes what gets filed, which the state file otherwise prevents.

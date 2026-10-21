# 3. Open with the last state, then refresh every tile

**Status:** Accepted  
**Date:** 2026-10-19

## Context

Quick settings query many tools (nmcli, bluetoothctl, makoctl, gsettings…); waiting for all of them before showing the panel made it feel slow.

## Decision

The panel opens immediately with each tile's last known state; every tile then refreshes in the background. Tiles whose tool or hardware is missing aren't shown.

## Consequences

- Opens instantly.
- A tile can show a stale state for a fraction of a second.

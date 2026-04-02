# Rule Flowchart Remedy Plan

## Purpose

This plan addresses the mismatch between the current AST rule builder UX and the intended product behavior. The current interface is labeled as a node graph, but it behaves like a nested syntax/tree editor with drag-to-reorder interactions. The remedy is to replace that interaction model with a real flowchart-style rule editor where users click nodes to configure logic.

## Problem Summary

The current `RuleBuilder` implementation does not provide an actual flowchart experience.

What exists today:

- Recursive card-based rendering of AST groups and conditions
- HTML drag-and-drop between groups
- Explicit move up and move down controls
- Inline form controls embedded directly inside each node card
- A synchronized JSON syntax editor

Why this is a problem:

- The UI promises a node graph, but the interaction model is a sortable tree
- Users are encouraged to think in list order instead of logical flow
- Up and down movement controls make the editor feel like a rule ranking tool
- Inline editing creates dense cards instead of compact, scannable nodes
- The current structure does not support pan, zoom, edge connections, or true node-based mental models

## Root Cause

The current graph mode was implemented as a recursive AST editor rather than a canvas-based graph editor.

Evidence from the current frontend:

- `frontend/src/components/RuleBuilder.tsx` uses recursive rendering of nested groups and conditions
- `moveNode` and `moveAstNode` encode list-style placement and reordering
- `DropLane` provides insertion lanes rather than graph connections
- `ArrowUp` and `ArrowDown` reinforce ordered-list semantics
- `frontend/package.json` does not include a graph library such as `reactflow`

This means the issue is architectural, not cosmetic.

## Recommended Remedy

### Short-term remedy

Rename the current mode so the product is honest about what it is.

Recommended copy changes:

- Change `Node graph` to `Tree editor` or `Visual AST editor`
- Update helper text to describe nested tree editing rather than graph editing

This does not fix the UX, but it stops misleading users immediately.

### Proper remedy

Replace the current graph mode with a true flowchart editor built on a graph/canvas library.

Recommended library:

- `reactflow`

Reason:

- Strong fit for React
- Supports nodes, edges, handles, pan, zoom, selection, and custom node rendering
- Works well for click-to-edit node workflows
- Lets us preserve the AST data model while presenting a real graph interaction layer

## Solution Principles

- Keep `RuleAst` as the persisted backend contract
- Treat the flowchart as a UI projection of the AST, not a new storage model
- Use compact visual nodes and a separate inspector panel for editing
- Remove list-order semantics from flowchart mode
- Preserve syntax mode as an advanced or parallel editing option
- Introduce the change incrementally so save/load behavior remains stable

## Target UX

The intended flowchart experience should behave like this:

- Users see a canvas with two root nodes:
  - `Must Have`
  - `Good to Have`
- Group nodes represent `AND` or `OR`
- Condition nodes represent leaf rules
- Edges show parent-child logic explicitly
- Clicking a node opens a side inspector or modal
- The inspector edits the selected node’s rule properties
- Adding a node happens from the selected node, not from inline row controls
- The canvas supports pan and zoom
- Node movement is spatial, not list-based

What should no longer define graph mode:

- Up/down reorder buttons
- Drop lanes between cards
- HTML `draggable` card sorting
- Large embedded forms inside every node

## Architecture Recommendation

### Source of truth

Continue using the existing `RuleAst` object as the source of truth for persistence and backend compatibility.

### New conversion layer

Add a conversion layer between persisted AST data and visual graph data.

Required helpers:

- `ruleAstToFlow(ast): { nodes, edges }`
- `flowSelectionToAstUpdate(...)`
- `insertChildNode(...)`
- `updateNodeConfig(...)`
- `removeNodeFromAst(...)`

The graph does not need to become the primary data model. It only needs to render and manipulate the AST cleanly.

### Node types

Recommended graph node types:

- `root`
  - Visual label for `Must Have` and `Good to Have`
- `group`
  - Displays combinator: `AND` or `OR`
  - Can accept child connections
- `condition`
  - Displays field, operator, and short value summary
  - Edits happen in inspector

### Editing pattern

Recommended editing pattern:

- Click node to select it
- Open right-side inspector
- Edit combinator or rule values in inspector
- Apply changes directly to AST-backed state

This keeps nodes readable and makes the graph feel like a flowchart rather than a form builder.

## Delivery Phases

### Phase 1: Honest labeling and groundwork

Goal: remove product confusion and prepare for the rewrite.

Build:

- Rename current `graph` mode copy to `Tree editor` or equivalent
- Update helper text to reflect current behavior
- Add `reactflow` dependency
- Create a dedicated `RuleFlowBuilder.tsx` component
- Introduce AST-to-flow helper utilities

Acceptance criteria:

- The current UI no longer claims to be a node graph
- The codebase has a clear integration point for the new flowchart builder

### Phase 2: Read-only flowchart rendering

Goal: render the current AST as a true visual graph before enabling editing.

Build:

- Render root, group, and condition nodes on a canvas
- Generate edges from AST parent-child relationships
- Support node selection
- Support pan and zoom
- Add visual distinction between root, group, and condition nodes

Acceptance criteria:

- Existing saved rules render as a real flowchart
- Users can visually understand rule relationships from edges and layout
- The flowchart works for nested groups

### Phase 3: Click-to-edit inspector

Goal: make node configuration happen from selection, not inline card forms.

Build:

- Add selected-node state
- Add side inspector for selected node
- Allow editing:
  - group combinator
  - condition field
  - condition data type
  - condition operator
  - condition value
  - condition secondary value
- Keep inspector updates synchronized with AST and syntax mode

Acceptance criteria:

- Clicking a node opens an editor
- Node cards remain compact and readable
- Edits immediately update the flowchart and syntax JSON

### Phase 4: Graph-native structure editing

Goal: create and remove nodes using graph semantics.

Build:

- Add actions from selected nodes to:
  - add condition child
  - add group child
  - delete selected node
- Support attaching new nodes under valid parents
- Preserve root node constraints
- Prevent illegal cycles or invalid insertions

Acceptance criteria:

- Users can build a rule graph without list-based drop lanes
- Group and condition insertion behaves predictably
- Deletion preserves valid AST structure

### Phase 5: Remove old fake-graph behavior

Goal: eliminate the interaction model that caused the original mismatch.

Build:

- Remove `ArrowUp` and `ArrowDown` controls from the flowchart mode
- Remove `DropLane` from the flowchart mode
- Remove HTML `draggable` behavior from the flowchart mode
- Keep syntax mode for advanced users
- Optionally keep the old tree editor behind a secondary mode if still useful internally

Acceptance criteria:

- Flowchart mode no longer feels like a sortable rule list
- Users interact with nodes and edges, not insertion lanes

## Implementation Notes

### Data model compatibility

No backend schema redesign is required for the initial remedy.

The existing recursive AST model is already suitable for:

- nested groups
- stable node IDs
- versioned persistence
- synchronized syntax editing

The frontend should adapt the presentation layer, not replace the storage contract.

### Layout strategy

Use a deterministic layout for the initial version so the graph is readable without manual arrangement.

Recommended starting point:

- vertical or left-to-right tree layout
- roots pinned at the top or left
- children auto-positioned beneath or after parent nodes

Manual node positioning can be considered later, but it is not required to solve the current problem.

### Inspector strategy

Avoid placing all rule fields directly inside nodes.

Recommended inspector sections:

- Node type
- Summary
- Combinator or condition settings
- Add child actions where valid
- Delete action where valid

This will make the graph cleaner and easier to scan.

## Risks and Mitigations

### Risk 1: Conversion bugs between AST and graph state

Mitigation:

- Keep AST as canonical state
- Derive nodes and edges from AST rather than maintaining two mutable models
- Add focused tests for nested group rendering and editing

### Risk 2: Rewrite disrupts save/load behavior

Mitigation:

- Reuse existing save pipeline unchanged
- Keep syntax mode available during rollout
- Test with real saved rulesets before removing the old UI

### Risk 3: Canvas complexity increases implementation time

Mitigation:

- Deliver in phases
- Start with read-only graph rendering
- Add editing after rendering is stable

### Risk 4: Users still need a structured text view

Mitigation:

- Preserve syntax mode
- Keep live synchronization between visual and JSON representations

## Testing Plan

### Frontend tests

- Render nested ASTs as graph nodes and edges
- Select a node and verify inspector contents
- Update a condition and confirm AST state changes
- Update a group combinator and confirm syntax view updates
- Add and remove nodes through graph actions
- Ensure invalid operations are blocked

### Manual verification

- Open an existing ruleset and confirm it renders as a graph
- Click condition node and edit field/operator/value
- Click group node and change combinator
- Add nested group under an existing group
- Save and reload the ruleset
- Compare syntax output before and after edits

## Acceptance Criteria

The remedy is complete when:

- The product no longer presents a sortable tree as a node graph
- Users can click a visual node to configure a rule
- The visual editor uses actual graph concepts: nodes, edges, canvas, and selection
- The saved AST remains backward compatible
- Syntax mode continues to reflect the same underlying rule structure

## Recommended Next Action

Implement the short-term label correction immediately, then begin the phased `reactflow` rewrite with `RuleAst` preserved as the canonical save format.

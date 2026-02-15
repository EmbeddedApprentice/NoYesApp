# NoYesApp Requirements

## Purpose

NoYesApp is a directed-graph questionnaire application. Each questionnaire is a graph of nodes connected by edges. Users navigate the graph by answering questions, reading statements, and reaching terminal endpoints.

## Graph Behavior

The questionnaire is a **directed graph** — loops and rejoins are allowed (not a strict tree).

### Node Types

- **Question**: Presents a YES/NO prompt. YES leads to one node, NO leads to a different node.
- **Statement**: Displays information. NEXT advances to a single next node.
- **Terminal**: A node with no outgoing edges. Reaching it ends the questionnaire.

### Edge Behavior

- Each edge has an **answer type** (YES, NO, or NEXT) and a **destination node**
- Question nodes have exactly two outgoing edges (YES and NO)
- Statement nodes have exactly one outgoing edge (NEXT)
- Terminal nodes have zero outgoing edges

### Extensibility

The data model must support future answer types beyond YES/NO (e.g., multiple choice, rating scales) without requiring a rewrite. The MVP keeps it simple with just YES/NO/NEXT.

## Database

Schema details TBD — to be discussed separately before implementation.

### Key Entities

- **Questionnaire** — a named graph of nodes; has a slug, owner, published status
- **Node** — a question, statement, or terminal within a questionnaire; has a slug, content, node type
- **Edge** — connects two nodes; has an answer type and destination
- **User** — authenticated account that creates/edits questionnaires
- **Response/Session** — records a user's path through a questionnaire

## User Accounts

- **Authenticated users** can create, edit, publish, and delete questionnaires
- **Anonymous users** can answer/navigate published questionnaires
- May require email from anonymous users to answer (TBD)

## Response History

Logged-in users can view their previously completed questionnaires and review their path through the graph — only the nodes they visited, not all nodes in the questionnaire.

## Pages

### Landing Page

Public page listing open/published questionnaires for anyone to try.

### About Page

Project information. Lists Claude as an author.

### Questionnaire Player

Public-facing UI for navigating a questionnaire node by node. Anonymous access allowed.

### Questionnaire Editor

Authenticated-only UI for creating and editing questionnaires (adding/removing nodes and edges, setting node types, configuring the graph).

### User Dashboard

Authenticated-only area showing the user's questionnaires and response history.

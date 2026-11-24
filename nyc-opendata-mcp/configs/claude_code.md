# Claude Code

Add the server for your user (all projects):

    claude mcp add --scope user nyc-opendata -- py -m nycod.server

Or for one batch folder only, put this in `.mcp.json` at its root:

    {"mcpServers": {"nyc-opendata": {"command": "py", "args": ["-m", "nycod.server"]}}}

Check it with `claude mcp list`; inside a session `/mcp` shows the 22 nycod_ tools.

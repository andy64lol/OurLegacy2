# TODO: Convert Game to Flask + Jinja2 SPA

## Goal
Create a modern single-page application (SPA) experience using Flask for the backend and Jinja2 for server-rendered templates, while preserving the existing game logic and assets.

## High-level tasks

1. Flask app structure
   - Refactor `app.py` / `main.py` into a clean Flask application.
   - Separate routes, API endpoints, and template rendering.
   - Add a `templates/` and `static/` organization if needed.

2. SPA shell and routing
   - Build a core SPA shell template using Jinja2.
   - Use client-side JavaScript to manage page views and navigation state.
   - Keep most game screens within a single page load.

3. API endpoints
   - Convert game actions into JSON-based Flask API routes.
   - Add endpoints for user state, game actions, inventory, shops, battles, etc.
   - Ensure authentication and session handling works with SPA requests.

4. Game UI integration
   - Move UI interactions to vanilla JS or small frontend modules in `static/js/`.
   - Use AJAX/fetch to call Flask APIs and update the UI dynamically.
   - Preserve existing templates as necessary, but prefer SPA partial updates.

5. Jinja2 template enhancements
   - Use Jinja2 for the base shell, initial state, and shared components.
   - Keep server-rendered markup for the first page load and authenticated layout.
   - Use JSON-encoded initial data for the SPA bootstrap.

6. Assets and static files
   - Ensure `static/css/`, `static/js/`, `static/fonts/`, and `static/` assets are served correctly.
   - Optimize asset loading for SPA behavior.

7. Testing and validation
   - Verify navigation works without full page refreshes.
   - Test game flows: login, play, shop, inventory, battles, and logout.
   - Confirm templates and API responses are stable.

## Notes
- Keep the existing game logic in `utilities/` and `game_data/` where possible.
- Focus on incremental migration: start with one major screen (e.g. play or dashboard) and expand.
- Maintain compatibility with current Flask/Jinja2 patterns used by the app.

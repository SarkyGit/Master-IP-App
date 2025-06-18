# Handling HTMX Modals

All pop-up dialogs are rendered into the empty `<div id="modal"></div>` found in `base.html`.
When a form inside a modal posts via HTMX, the response replaces this container.

Returning an HTTP 204 status will leave the dialog in place because HTMX does not modify the DOM.
Instead, return HTML that clears the container or provide a snippet that does so.

Example:

```python
if request.headers.get("HX-Request"):
    return templates.TemplateResponse("close_modal.html", {"request": request})
```

The `close_modal.html` template simply empties the modal element:

```html
<div id="modal"></div>
```

This pattern ensures the modal disappears after a successful action.

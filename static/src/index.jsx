import React from 'react';
import { createRoot } from 'react-dom/client';
import { AdminMenu } from './adminMenu.jsx';

document.querySelectorAll('[data-admin-menu]').forEach((el) => {
  const label = el.getAttribute('data-label');
  const items = JSON.parse(el.getAttribute('data-items'));
  const root = createRoot(el);
  root.render(<AdminMenu label={label} items={items} />);
});

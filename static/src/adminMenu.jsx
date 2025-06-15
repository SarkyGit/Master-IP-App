import React from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

export function AdminMenu({ label, items }) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="px-4 py-2 text-blue-400 border rounded hover:bg-gray-700">
          {label}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="absolute right-0 mt-2 bg-gray-800 text-white py-2 w-48">
          {items.map((item, idx) => (
            <DropdownMenu.Item key={idx} className="block">
              <a className="block px-4 py-2 text-blue-400 rounded hover:bg-gray-700" href={item.href}>{item.label}</a>
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

export type PaginationMeta = {
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type PaginatedCollection<Item> = {
  data: Item[];
  pagination: PaginationMeta | null;
};

export type PaginatedPayload<Key extends string, Item> = {
  [key in Key]: Item[];
} & {
  pagination?: PaginationMeta | null;
};

export function normalizePaginatedPayload<Key extends string, Item>(
  payload: PaginatedPayload<Key, Item>,
  key: Key,
): PaginatedCollection<Item> {
  return {
    data: payload[key] ?? [],
    pagination: payload.pagination ?? null,
  };
}

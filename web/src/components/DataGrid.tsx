import {
  useMantineReactTable,
  type MRT_ColumnDef,
  type MRT_SortingState,
} from "mantine-react-table";

/**
 * Shared dense-grid config so every screen (League, Pro, FIV, Dynasty, My Team)
 * looks and behaves identically: compact rows, faceted filters, global search,
 * sticky scroll container. Pass columns + data; optionally a default sort.
 */
export function useDataGrid<T extends Record<string, any>>(
  columns: MRT_ColumnDef<T>[],
  data: T[],
  opts: {
    isLoading?: boolean;
    sorting?: MRT_SortingState;
    maxHeight?: string;
    paginateOver?: number;
  } = {},
) {
  const { isLoading = false, sorting, maxHeight = "65vh", paginateOver = 50 } = opts;
  return useMantineReactTable({
    columns,
    data,
    state: { isLoading },
    enablePagination: data.length > paginateOver,
    initialState: {
      density: "xs",
      pagination: { pageSize: paginateOver, pageIndex: 0 },
      showGlobalFilter: true,
      ...(sorting ? { sorting } : {}),
    },
    mantineTableProps: { striped: true, highlightOnHover: true },
    mantineTableContainerProps: { style: { maxHeight } },
  });
}

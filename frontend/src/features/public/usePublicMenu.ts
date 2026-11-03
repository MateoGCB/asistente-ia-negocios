import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPublicMenu } from "../../api/endpoints";
import { isApiError } from "../../api/errors";
import { queryKeys } from "../../app/queryKeys";
import { toCents } from "../../lib/money";

// The public menu of a slug, shared by the three customer screens (cached by TanStack Query)
export function usePublicMenu(slug: string) {
  const query = useQuery({ queryKey: queryKeys.publicMenu(slug), queryFn: () => getPublicMenu(slug) });
  // Unknown slug, archived branch or branch without menu: the backend answers the same 404
  const unavailable = query.isError && isApiError(query.error) && query.error.kind === "not_found";
  const priceCents = useMemo(
    () => new Map((query.data?.items ?? []).map((item) => [item.id, toCents(item.price)])),
    [query.data],
  );
  return { ...query, unavailable, priceCents };
}

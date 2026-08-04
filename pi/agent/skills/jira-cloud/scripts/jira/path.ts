export function requireNonEmpty(value: string, name: string): string {
	if (!value) throw new TypeError(`${name} must not be empty`);
	return value;
}

export function encodePathSegment(value: string, name: string): string {
	return encodeURIComponent(requireNonEmpty(value, name));
}

export function appendQuery(
	path: string,
	values: Record<string, string | number | boolean | string[] | undefined>,
): string {
	const query = new URLSearchParams();
	for (const [name, value] of Object.entries(values)) {
		if (value === undefined) continue;
		query.set(name, Array.isArray(value) ? value.join(",") : String(value));
	}
	const serialized = query.toString();
	return serialized ? `${path}?${serialized}` : path;
}

import { appendQuery, encodePathSegment } from "../path.ts";
import type { JiraRequester } from "../transport.ts";
import type {
	AdfDocument,
	JiraComment,
	JiraPage,
	ListCommentsOptions,
} from "../types.ts";

export class CommentResource {
	readonly #requester: JiraRequester;

	constructor(requester: JiraRequester) {
		this.#requester = requester;
	}

	list(
		issueKey: string,
		options: ListCommentsOptions = {},
	): Promise<JiraPage<JiraComment>> {
		const key = encodePathSegment(issueKey, "issueKey");
		const path = appendQuery(`/rest/api/3/issue/${key}/comment`, {
			startAt: options.startAt,
			maxResults: options.maxResults,
			orderBy: options.orderBy,
			expand: options.expand,
		});
		return this.#requester.get<JiraPage<JiraComment>>(path);
	}

	add(issueKey: string, document: AdfDocument): Promise<JiraComment> {
		const key = encodePathSegment(issueKey, "issueKey");
		return this.#requester.post<JiraComment>(
			`/rest/api/3/issue/${key}/comment`,
			{ body: document },
		);
	}

	update(
		issueKey: string,
		commentId: string,
		document: AdfDocument,
	): Promise<JiraComment> {
		const key = encodePathSegment(issueKey, "issueKey");
		const id = encodePathSegment(commentId, "commentId");
		return this.#requester.put<JiraComment>(
			`/rest/api/3/issue/${key}/comment/${id}`,
			{ body: document },
		);
	}

	remove(issueKey: string, commentId: string): Promise<void> {
		const key = encodePathSegment(issueKey, "issueKey");
		const id = encodePathSegment(commentId, "commentId");
		return this.#requester.delete<void>(
			`/rest/api/3/issue/${key}/comment/${id}`,
		);
	}
}

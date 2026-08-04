import type { JiraRequester } from "../transport.ts";
import type {
	JiraIssue,
	SearchIssuesRequest,
	SearchIssuesResult,
} from "../types.ts";

export class SearchResource {
	readonly #requester: JiraRequester;

	constructor(requester: JiraRequester) {
		this.#requester = requester;
	}

	issues<T = JiraIssue>(
		request: SearchIssuesRequest,
	): Promise<SearchIssuesResult<T>> {
		return this.#requester.post<SearchIssuesResult<T>>(
			"/rest/api/3/search/jql",
			request,
		);
	}
}

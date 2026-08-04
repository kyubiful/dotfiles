import { encodePathSegment } from "../path.ts";
import type { JiraRequester } from "../transport.ts";
import type { AddWorklogRequest, JiraWorklog } from "../types.ts";

export class WorklogResource {
	readonly #requester: JiraRequester;

	constructor(requester: JiraRequester) {
		this.#requester = requester;
	}

	add(issueKey: string, request: AddWorklogRequest): Promise<JiraWorklog> {
		const key = encodePathSegment(issueKey, "issueKey");
		return this.#requester.post<JiraWorklog>(
			`/rest/api/3/issue/${key}/worklog`,
			request,
		);
	}
}

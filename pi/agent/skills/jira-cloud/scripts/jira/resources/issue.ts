import { appendQuery, encodePathSegment, requireNonEmpty } from "../path.ts";
import type { JiraRequester } from "../transport.ts";
import type {
	CreateIssueRequest,
	CreatedIssue,
	GetIssueOptions,
	JiraIssue,
	JiraTransitionsResult,
	TransitionIssueOptions,
	UpdateIssueRequest,
} from "../types.ts";

export class IssueResource {
	readonly #requester: JiraRequester;

	constructor(requester: JiraRequester) {
		this.#requester = requester;
	}

	get<T = JiraIssue>(
		issueKey: string,
		options: GetIssueOptions = {},
	): Promise<T> {
		const key = encodePathSegment(issueKey, "issueKey");
		const path = appendQuery(`/rest/api/3/issue/${key}`, {
			fields: options.fields,
			expand: options.expand,
			properties: options.properties,
			fieldsByKeys: options.fieldsByKeys,
			updateHistory: options.updateHistory,
		});
		return this.#requester.get<T>(path);
	}

	create(request: CreateIssueRequest): Promise<CreatedIssue> {
		return this.#requester.post<CreatedIssue>("/rest/api/3/issue", request);
	}

	update(issueKey: string, request: UpdateIssueRequest): Promise<void> {
		const key = encodePathSegment(issueKey, "issueKey");
		return this.#requester.put<void>(`/rest/api/3/issue/${key}`, request);
	}

	assign(issueKey: string, accountId: string | null): Promise<void> {
		const key = encodePathSegment(issueKey, "issueKey");
		return this.#requester.put<void>(`/rest/api/3/issue/${key}/assignee`, {
			accountId,
		});
	}

	transitions(issueKey: string): Promise<JiraTransitionsResult> {
		const key = encodePathSegment(issueKey, "issueKey");
		return this.#requester.get<JiraTransitionsResult>(
			`/rest/api/3/issue/${key}/transitions`,
		);
	}

	transition(
		issueKey: string,
		transitionId: string,
		options: TransitionIssueOptions = {},
	): Promise<void> {
		const key = encodePathSegment(issueKey, "issueKey");
		const id = requireNonEmpty(transitionId, "transitionId");
		return this.#requester.post<void>(`/rest/api/3/issue/${key}/transitions`, {
			...options,
			transition: { id },
		});
	}
}

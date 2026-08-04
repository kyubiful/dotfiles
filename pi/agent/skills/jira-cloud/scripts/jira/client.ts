import { CommentResource } from "./resources/comment.ts";
import { IssueResource } from "./resources/issue.ts";
import { SearchResource } from "./resources/search.ts";
import { WorklogResource } from "./resources/worklog.ts";
import { JiraTransport, loadJiraOptionsFromEnvironment } from "./transport.ts";
import type { JiraRequester } from "./transport.ts";
import type { JiraClientOptions } from "./types.ts";

export class JiraClient {
	readonly issue: IssueResource;
	readonly comment: CommentResource;
	readonly worklog: WorklogResource;
	readonly search: SearchResource;
	readonly get: JiraRequester["get"];
	readonly post: JiraRequester["post"];
	readonly put: JiraRequester["put"];
	readonly delete: JiraRequester["delete"];

	constructor(options: JiraClientOptions) {
		const transport = new JiraTransport(options);
		this.issue = new IssueResource(transport);
		this.comment = new CommentResource(transport);
		this.worklog = new WorklogResource(transport);
		this.search = new SearchResource(transport);
		this.get = transport.get.bind(transport);
		this.post = transport.post.bind(transport);
		this.put = transport.put.bind(transport);
		this.delete = transport.delete.bind(transport);
	}

	static fromEnvironment(
		environment: Record<string, string | undefined> = process.env,
	): JiraClient {
		return new JiraClient(loadJiraOptionsFromEnvironment(environment));
	}
}

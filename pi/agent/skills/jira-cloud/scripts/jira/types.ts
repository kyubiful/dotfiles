export type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

export type JiraClientOptions = {
	baseUrl: string | URL;
	email: string;
	apiToken: string;
	timeoutMs?: number;
	maxResponseBytes?: number;
};

export type RawJiraResponse = {
	statusCode: number;
	body: string;
};

export type AdfNode = {
	type: string;
	attrs?: Record<string, unknown>;
	content?: AdfNode[];
	marks?: Array<{ type: string; attrs?: Record<string, unknown> }>;
	text?: string;
};

export type AdfDocument = {
	version: 1;
	type: "doc";
	content: AdfNode[];
};

export type JiraIssue = {
	id: string;
	key: string;
	self?: string;
	fields: Record<string, unknown>;
};

export type CreatedIssue = {
	id: string;
	key: string;
	self: string;
	transition?: {
		status: number;
		errorCollection?: unknown;
	};
};

export type CreateIssueRequest = {
	fields: Record<string, unknown>;
	update?: Record<string, unknown>;
	transition?: { id: string };
	properties?: Array<{ key: string; value: unknown }>;
};

export type UpdateIssueRequest = {
	fields?: Record<string, unknown>;
	update?: Record<string, unknown>;
	properties?: Array<{ key: string; value: unknown }>;
	historyMetadata?: Record<string, unknown>;
};

export type GetIssueOptions = {
	fields?: string[];
	expand?: string[];
	properties?: string[];
	fieldsByKeys?: boolean;
	updateHistory?: boolean;
};

export type TransitionIssueOptions = {
	fields?: Record<string, unknown>;
	update?: Record<string, unknown>;
	historyMetadata?: Record<string, unknown>;
};

export type JiraTransition = {
	id: string;
	name: string;
	to?: Record<string, unknown>;
	hasScreen?: boolean;
	isGlobal?: boolean;
	isInitial?: boolean;
	isAvailable?: boolean;
	isConditional?: boolean;
};

export type JiraTransitionsResult = {
	expand?: string;
	transitions: JiraTransition[];
};

export type JiraUser = {
	accountId?: string;
	displayName?: string;
	emailAddress?: string;
	active?: boolean;
	[key: string]: unknown;
};

export type JiraComment = {
	id: string;
	self?: string;
	body: AdfDocument;
	author?: JiraUser;
	created?: string;
	updated?: string;
	[key: string]: unknown;
};

export type JiraPage<T> = {
	startAt?: number;
	maxResults?: number;
	total?: number;
	isLast?: boolean;
	nextPageToken?: string;
	values?: T[];
	issues?: T[];
	comments?: T[];
	worklogs?: T[];
};

export type ListCommentsOptions = {
	startAt?: number;
	maxResults?: number;
	orderBy?: "created" | "-created";
	expand?: string[];
};

export type JiraWorklog = {
	id: string;
	self?: string;
	issueId?: string;
	timeSpent?: string;
	timeSpentSeconds?: number;
	comment?: AdfDocument;
	[key: string]: unknown;
};

export type AddWorklogRequest = {
	timeSpent?: string;
	timeSpentSeconds?: number;
	started?: string;
	comment?: AdfDocument;
	visibility?: Record<string, unknown>;
	properties?: Array<{ key: string; value: unknown }>;
	remainingEstimate?: string;
};

export type SearchIssuesRequest = {
	jql: string;
	fields?: string[];
	expand?: string;
	maxResults?: number;
	nextPageToken?: string;
	properties?: string[];
	fieldsByKeys?: boolean;
	reconcileIssues?: number[];
};

export type SearchIssuesResult<T = JiraIssue> = {
	issues: T[];
	nextPageToken?: string;
	isLast?: boolean;
};

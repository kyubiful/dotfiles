import assert from "node:assert/strict";
import test from "node:test";

import {
	CommentResource,
	IssueResource,
	JiraClient,
	JiraConfigurationError,
	JiraTransport,
	SearchResource,
	WorklogResource,
	loadJiraOptionsFromEnvironment,
} from "./index.ts";
import { executeJiraCommand, parseCommandArguments } from "./command.ts";

class RecordingRequester {
	calls = [];
	response = { ok: true };

	get(path) {
		this.calls.push(["GET", path]);
		return Promise.resolve(this.response);
	}

	post(path, body) {
		this.calls.push(["POST", path, body]);
		return Promise.resolve(this.response);
	}

	put(path, body) {
		this.calls.push(["PUT", path, body]);
		return Promise.resolve(this.response);
	}

	delete(path) {
		this.calls.push(["DELETE", path]);
		return Promise.resolve(this.response);
	}
}

const document = {
	version: 1,
	type: "doc",
	content: [{ type: "paragraph", content: [{ type: "text", text: "Done" }] }],
};

test("JiraClient exposes grouped resources", () => {
	const jira = new JiraClient({
		baseUrl: "https://example.atlassian.net",
		email: "user@example.com",
		apiToken: "secret",
	});

	assert.ok(jira.issue instanceof IssueResource);
	assert.ok(jira.comment instanceof CommentResource);
	assert.ok(jira.worklog instanceof WorklogResource);
	assert.ok(jira.search instanceof SearchResource);
});

test("IssueResource builds issue operations", async () => {
	const requester = new RecordingRequester();
	const issue = new IssueResource(requester);

	await issue.get("PAY/42", {
		fields: ["summary", "status"],
		fieldsByKeys: true,
	});
	await issue.create({ fields: { summary: "Example" } });
	await issue.assign("PAY-42", "account-1");
	await issue.transition("PAY-42", "31", {
		fields: { resolution: { name: "Done" } },
	});

	assert.deepEqual(requester.calls, [
		[
			"GET",
			"/rest/api/3/issue/PAY%2F42?fields=summary%2Cstatus&fieldsByKeys=true",
		],
		["POST", "/rest/api/3/issue", { fields: { summary: "Example" } }],
		["PUT", "/rest/api/3/issue/PAY-42/assignee", { accountId: "account-1" }],
		[
			"POST",
			"/rest/api/3/issue/PAY-42/transitions",
			{
				fields: { resolution: { name: "Done" } },
				transition: { id: "31" },
			},
		],
	]);
});

test("Comment, worklog, and search resources build their operations", async () => {
	const requester = new RecordingRequester();

	await new CommentResource(requester).add("PAY-42", document);
	await new WorklogResource(requester).add("PAY-42", {
		timeSpentSeconds: 3600,
	});
	await new SearchResource(requester).issues({
		jql: "project = PAY",
		maxResults: 25,
	});

	assert.deepEqual(requester.calls, [
		["POST", "/rest/api/3/issue/PAY-42/comment", { body: document }],
		["POST", "/rest/api/3/issue/PAY-42/worklog", { timeSpentSeconds: 3600 }],
		[
			"POST",
			"/rest/api/3/search/jql",
			{ jql: "project = PAY", maxResults: 25 },
		],
	]);
});

test("JiraTransport redacts raw and encoded credentials", () => {
	const email = "user@example.com";
	const apiToken = "very-secret-token";
	const authorization = `Basic ${Buffer.from(`${email}:${apiToken}`).toString("base64")}`;
	const transport = new JiraTransport({
		baseUrl: "https://example.atlassian.net",
		email,
		apiToken,
	});

	const redacted = transport.redact(`${apiToken} ${authorization}`);
	assert.equal(redacted, "[REDACTED] [REDACTED]");
});

test("environment loading reports all missing values", () => {
	assert.throws(
		() => loadJiraOptionsFromEnvironment({}),
		(error) => {
			assert.ok(error instanceof JiraConfigurationError);
			assert.match(error.message, /JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN/);
			return true;
		},
	);
});

test("resource-oriented commands dispatch through JiraClient resources", async () => {
	const requester = new RecordingRequester();
	const jira = {
		issue: new IssueResource(requester),
		comment: new CommentResource(requester),
		worklog: new WorklogResource(requester),
		search: new SearchResource(requester),
		get: requester.get.bind(requester),
		post: requester.post.bind(requester),
		put: requester.put.bind(requester),
		delete: requester.delete.bind(requester),
	};

	const addComment = parseCommandArguments([
		"comment.add",
		"--issue",
		"PAY-42",
		"--data-file",
		"comment.json",
	]);
	await executeJiraCommand(jira, addComment, document);

	const unassign = parseCommandArguments([
		"issue.assign",
		"--issue",
		"PAY-42",
		"--account-id",
		"null",
	]);
	await executeJiraCommand(jira, unassign);

	assert.deepEqual(requester.calls, [
		["POST", "/rest/api/3/issue/PAY-42/comment", { body: document }],
		["PUT", "/rest/api/3/issue/PAY-42/assignee", { accountId: null }],
	]);
});

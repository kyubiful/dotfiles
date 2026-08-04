/// <reference path="../node-shim.d.ts" />

import { readFile } from "node:fs/promises";

import type { JiraClient } from "./client.ts";
import type {
	AddWorklogRequest,
	AdfDocument,
	CreateIssueRequest,
	GetIssueOptions,
	ListCommentsOptions,
	SearchIssuesRequest,
	TransitionIssueOptions,
	UpdateIssueRequest,
} from "./types.ts";

const OPERATIONS = [
	"myself",
	"issue.get",
	"issue.create",
	"issue.update",
	"issue.assign",
	"issue.transitions",
	"issue.transition",
	"comment.list",
	"comment.add",
	"comment.update",
	"comment.remove",
	"worklog.add",
	"search.issues",
	"raw.get",
	"raw.post",
	"raw.put",
	"raw.delete",
] as const;

export type JiraOperation = (typeof OPERATIONS)[number];

export type JiraCommandArguments = {
	operation: JiraOperation;
	issue?: string;
	comment?: string;
	transition?: string;
	accountId?: string | null;
	path?: string;
	data?: string;
	dataFile?: string;
};

const OPERATIONS_SET = new Set<string>(OPERATIONS);
const FLAG_NAMES = [
	"--issue",
	"--comment",
	"--transition",
	"--account-id",
	"--path",
	"--data",
	"--data-file",
] as const;
type CommandFlag = (typeof FLAG_NAMES)[number];
const FLAGS = new Set<string>(FLAG_NAMES);
const APPLY_FLAG: Record<
	CommandFlag,
	(args: JiraCommandArguments, value: string) => void
> = {
	"--issue": (args, value) => {
		args.issue = value;
	},
	"--comment": (args, value) => {
		args.comment = value;
	},
	"--transition": (args, value) => {
		args.transition = value;
	},
	"--account-id": (args, value) => {
		args.accountId = value === "null" ? null : value;
	},
	"--path": (args, value) => {
		args.path = value;
	},
	"--data": (args, value) => {
		args.data = value;
	},
	"--data-file": (args, value) => {
		args.dataFile = value;
	},
};

function commandError(message: string): Error {
	const error = new Error(message);
	error.name = "JiraCommandError";
	return error;
}

export function parseCommandArguments(argv: string[]): JiraCommandArguments {
	const operation = argv[0];
	if (!operation || !OPERATIONS_SET.has(operation)) {
		throw commandError(`operation must be one of: ${OPERATIONS.join(", ")}`);
	}

	const args: JiraCommandArguments = {
		operation: operation as JiraOperation,
	};
	for (let index = 1; index < argv.length; index += 2) {
		const flag = argv[index];
		const value = argv[index + 1];
		if (!FLAGS.has(flag)) throw commandError(`unknown argument: ${flag}`);
		if (value === undefined || value === "") {
			throw commandError(`missing value for ${flag}`);
		}

		APPLY_FLAG[flag as CommandFlag](args, value);
	}
	if (args.data !== undefined && args.dataFile !== undefined) {
		throw commandError("use either --data or --data-file, not both");
	}
	return args;
}

export async function loadCommandPayload(
	args: JiraCommandArguments,
): Promise<unknown> {
	let source = args.data;
	if (args.dataFile) {
		try {
			source = await readFile(args.dataFile, "utf8");
		} catch (error) {
			const detail = error instanceof Error ? error.message : "unknown error";
			throw commandError(`cannot read --data-file: ${detail}`);
		}
	}
	if (source === undefined) return undefined;

	try {
		return JSON.parse(source) as unknown;
	} catch {
		throw commandError("request body is not valid JSON");
	}
}

function requireValue(value: string | undefined, flag: string): string {
	if (!value) throw commandError(`${flag} is required for this operation`);
	return value;
}

function requireAccountId(value: string | null | undefined): string | null {
	if (value === undefined) {
		throw commandError("--account-id is required for this operation");
	}
	return value;
}

function requirePayload<T>(payload: unknown): T {
	if (payload === undefined) {
		throw commandError("--data or --data-file is required for this operation");
	}
	if (
		payload === null ||
		typeof payload !== "object" ||
		Array.isArray(payload)
	) {
		throw commandError("request body must be a JSON object");
	}
	return payload as T;
}

function optionalPayload<T>(payload: unknown): T {
	return payload === undefined ? ({} as T) : requirePayload<T>(payload);
}

type CommandHandler = (
	jira: JiraClient,
	args: JiraCommandArguments,
	payload: unknown,
) => Promise<unknown>;

const issueKey = (args: JiraCommandArguments): string =>
	requireValue(args.issue, "--issue");
const commentId = (args: JiraCommandArguments): string =>
	requireValue(args.comment, "--comment");
const transitionId = (args: JiraCommandArguments): string =>
	requireValue(args.transition, "--transition");
const rawPath = (args: JiraCommandArguments): string =>
	requireValue(args.path, "--path");

const COMMAND_HANDLERS: Record<JiraOperation, CommandHandler> = {
	myself: (jira) => jira.get("/rest/api/3/myself"),
	"issue.get": (jira, args, payload) =>
		jira.issue.get(issueKey(args), optionalPayload<GetIssueOptions>(payload)),
	"issue.create": (jira, _args, payload) =>
		jira.issue.create(requirePayload<CreateIssueRequest>(payload)),
	"issue.update": (jira, args, payload) =>
		jira.issue.update(
			issueKey(args),
			requirePayload<UpdateIssueRequest>(payload),
		),
	"issue.assign": (jira, args) =>
		jira.issue.assign(issueKey(args), requireAccountId(args.accountId)),
	"issue.transitions": (jira, args) => jira.issue.transitions(issueKey(args)),
	"issue.transition": (jira, args, payload) =>
		jira.issue.transition(
			issueKey(args),
			transitionId(args),
			optionalPayload<TransitionIssueOptions>(payload),
		),
	"comment.list": (jira, args, payload) =>
		jira.comment.list(
			issueKey(args),
			optionalPayload<ListCommentsOptions>(payload),
		),
	"comment.add": (jira, args, payload) =>
		jira.comment.add(issueKey(args), requirePayload<AdfDocument>(payload)),
	"comment.update": (jira, args, payload) =>
		jira.comment.update(
			issueKey(args),
			commentId(args),
			requirePayload<AdfDocument>(payload),
		),
	"comment.remove": (jira, args) =>
		jira.comment.remove(issueKey(args), commentId(args)),
	"worklog.add": (jira, args, payload) =>
		jira.worklog.add(
			issueKey(args),
			requirePayload<AddWorklogRequest>(payload),
		),
	"search.issues": (jira, _args, payload) =>
		jira.search.issues(requirePayload<SearchIssuesRequest>(payload)),
	"raw.get": (jira, args) => jira.get(rawPath(args)),
	"raw.post": (jira, args, payload) =>
		jira.post(rawPath(args), requirePayload<Record<string, unknown>>(payload)),
	"raw.put": (jira, args, payload) =>
		jira.put(rawPath(args), requirePayload<Record<string, unknown>>(payload)),
	"raw.delete": (jira, args) => jira.delete(rawPath(args)),
};

export function executeJiraCommand(
	jira: JiraClient,
	args: JiraCommandArguments,
	payload: unknown,
): Promise<unknown> {
	const handler = COMMAND_HANDLERS[args.operation];
	if (!handler) {
		return Promise.reject(
			commandError(`unsupported operation: ${String(args.operation)}`),
		);
	}
	return handler(jira, args, payload);
}

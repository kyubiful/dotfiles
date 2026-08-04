#!/usr/bin/env node
/** Resource-oriented Jira Cloud CLI backed by JiraClient. */

/// <reference path="./node-shim.d.ts" />

import {
	JiraApiError,
	JiraClient,
	JiraConfigurationError,
	loadJiraOptionsFromEnvironment,
} from "./jira/index.ts";
import type { JiraClientOptions } from "./jira/index.ts";
import {
	executeJiraCommand,
	loadCommandPayload,
	parseCommandArguments,
} from "./jira/command.ts";

function writeError(message: string): void {
	process.stderr.write(`${message}\n`);
}

function createRedactor(options: JiraClientOptions): (value: string) => string {
	const authorization = `Basic ${Buffer.from(
		`${options.email}:${options.apiToken}`,
	).toString("base64")}`;
	return (value) =>
		value
			.replaceAll(options.apiToken, "[REDACTED]")
			.replaceAll(authorization, "[REDACTED]");
}

async function main(): Promise<void> {
	let redact = (value: string): string => value;
	try {
		const args = parseCommandArguments(process.argv.slice(2));
		const payload = await loadCommandPayload(args);
		const options = loadJiraOptionsFromEnvironment();
		redact = createRedactor(options);
		const result = await executeJiraCommand(
			new JiraClient(options),
			args,
			payload,
		);
		if (result !== undefined) {
			process.stdout.write(`${redact(JSON.stringify(result))}\n`);
		}
	} catch (error) {
		const message = error instanceof Error ? error.message : "unknown error";
		const expected =
			error instanceof JiraApiError ||
			error instanceof JiraConfigurationError ||
			(error instanceof Error && error.name === "JiraCommandError");
		writeError(`jira: ${expected ? "" : "request failed: "}${redact(message)}`);
		if (error instanceof JiraApiError && error.responseBody) {
			writeError(redact(error.responseBody));
		}
		process.exitCode = 1;
	}
}

void main();

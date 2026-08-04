/// <reference path="../node-shim.d.ts" />

import https from "node:https";

import { JiraApiError, JiraConfigurationError } from "./errors.ts";
import type {
	HttpMethod,
	JiraClientOptions,
	RawJiraResponse,
} from "./types.ts";

const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024;
const REQUIRED_ENV = ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"] as const;

export interface JiraRequester {
	get<T>(path: string): Promise<T>;
	post<T>(path: string, body: unknown): Promise<T>;
	put<T>(path: string, body: unknown): Promise<T>;
	delete<T>(path: string): Promise<T>;
}

export function loadJiraOptionsFromEnvironment(
	environment: Record<string, string | undefined> = process.env,
): JiraClientOptions {
	const missing = REQUIRED_ENV.filter((name) => !environment[name]);
	if (missing.length > 0) {
		throw new JiraConfigurationError(
			`missing required environment variables: ${missing.join(", ")}`,
		);
	}

	return {
		baseUrl: environment.JIRA_BASE_URL as string,
		email: environment.JIRA_EMAIL as string,
		apiToken: environment.JIRA_API_TOKEN as string,
	};
}

function validatePositiveInteger(value: number, name: string): number {
	if (!Number.isSafeInteger(value) || value <= 0) {
		throw new JiraConfigurationError(`${name} must be a positive integer`);
	}
	return value;
}

function validateBaseUrl(value: string | URL): URL {
	let baseUrl: URL;
	try {
		baseUrl = new URL(value);
	} catch {
		throw new JiraConfigurationError(
			"JIRA_BASE_URL must be a valid HTTPS Jira Cloud URL",
		);
	}

	if (
		baseUrl.protocol !== "https:" ||
		!baseUrl.hostname ||
		baseUrl.username ||
		baseUrl.password ||
		baseUrl.pathname !== "/" ||
		baseUrl.search ||
		baseUrl.hash
	) {
		throw new JiraConfigurationError(
			"JIRA_BASE_URL must be an HTTPS Jira Cloud URL without a path or embedded credentials",
		);
	}
	return baseUrl;
}

function validatePath(path: string): void {
	if (!path.startsWith("/") || path.includes("://")) {
		throw new JiraConfigurationError(
			"request path must be a relative Jira REST path beginning with /",
		);
	}
}

export class JiraTransport implements JiraRequester {
	readonly #baseUrl: URL;
	readonly #authorization: string;
	readonly #apiToken: string;
	readonly #timeoutMs: number;
	readonly #maxResponseBytes: number;

	constructor(options: JiraClientOptions) {
		if (!options.email || !options.apiToken) {
			throw new JiraConfigurationError(
				"Jira email and API token must not be empty",
			);
		}
		this.#baseUrl = validateBaseUrl(options.baseUrl);
		this.#apiToken = options.apiToken;
		this.#authorization = `Basic ${Buffer.from(
			`${options.email}:${options.apiToken}`,
		).toString("base64")}`;
		this.#timeoutMs = validatePositiveInteger(
			options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
			"timeoutMs",
		);
		this.#maxResponseBytes = validatePositiveInteger(
			options.maxResponseBytes ?? DEFAULT_MAX_RESPONSE_BYTES,
			"maxResponseBytes",
		);
	}

	get<T>(path: string): Promise<T> {
		return this.request<T>("GET", path);
	}

	post<T>(path: string, body: unknown): Promise<T> {
		return this.request<T>("POST", path, body);
	}

	put<T>(path: string, body: unknown): Promise<T> {
		return this.request<T>("PUT", path, body);
	}

	delete<T>(path: string): Promise<T> {
		return this.request<T>("DELETE", path);
	}

	async request<T>(
		method: HttpMethod,
		path: string,
		body?: unknown,
	): Promise<T> {
		let payload: string | undefined;
		if (body !== undefined) {
			try {
				payload = JSON.stringify(body);
			} catch {
				throw new JiraConfigurationError(
					"request body must be JSON-serializable",
				);
			}
			if (payload === undefined) {
				throw new JiraConfigurationError(
					"request body must be JSON-serializable",
				);
			}
		}

		const result = await this.requestRaw(method, path, payload);
		if (result.statusCode < 200 || result.statusCode >= 300) {
			throw new JiraApiError(result.statusCode, this.redact(result.body));
		}
		if (!result.body) return undefined as T;

		try {
			return JSON.parse(result.body) as T;
		} catch {
			throw new JiraApiError(
				result.statusCode,
				"Jira returned a non-JSON response",
			);
		}
	}

	requestRaw(
		method: HttpMethod,
		path: string,
		payload?: string,
	): Promise<RawJiraResponse> {
		validatePath(path);

		return new Promise((resolve, reject) => {
			let settled = false;
			const resolveOnce = (response: RawJiraResponse): void => {
				if (settled) return;
				settled = true;
				resolve(response);
			};
			const rejectOnce = (error: Error): void => {
				if (settled) return;
				settled = true;
				reject(error);
			};

			const request = https.request(
				{
					protocol: "https:",
					hostname: this.#baseUrl.hostname,
					port: this.#baseUrl.port || undefined,
					method,
					path,
					headers: {
						Accept: "application/json",
						Authorization: this.#authorization,
						...(payload === undefined
							? {}
							: {
									"Content-Type": "application/json",
									"Content-Length": Buffer.byteLength(payload),
								}),
					},
				},
				(response) => {
					const chunks: Buffer[] = [];
					let receivedBytes = 0;

					response.on("data", (chunk: Buffer) => {
						receivedBytes += chunk.length;
						if (receivedBytes > this.#maxResponseBytes) {
							response.destroy(
								new Error(
									`Jira response exceeded ${this.#maxResponseBytes} bytes`,
								),
							);
							return;
						}
						chunks.push(chunk);
					});
					response.on("end", () => {
						resolveOnce({
							statusCode: response.statusCode ?? 0,
							body: Buffer.concat(chunks).toString("utf8"),
						});
					});
					response.on("aborted", () => {
						rejectOnce(new Error("Jira response was aborted"));
					});
					response.on("error", rejectOnce);
				},
			);

			request.setTimeout(this.#timeoutMs, () => {
				request.destroy(
					new Error(`Jira request timed out after ${this.#timeoutMs} ms`),
				);
			});
			request.on("error", rejectOnce);
			if (payload !== undefined) request.write(payload);
			request.end();
		});
	}

	redact(value: string): string {
		return value
			.replaceAll(this.#apiToken, "[REDACTED]")
			.replaceAll(this.#authorization, "[REDACTED]");
	}
}

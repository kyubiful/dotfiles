export class JiraApiError extends Error {
	readonly statusCode: number;
	readonly responseBody: string;

	constructor(statusCode: number, responseBody: string) {
		super(`Jira returned HTTP ${statusCode}`);
		this.name = "JiraApiError";
		this.statusCode = statusCode;
		this.responseBody = responseBody;
	}
}

export class JiraConfigurationError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "JiraConfigurationError";
	}
}

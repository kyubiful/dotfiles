declare const process: {
	argv: string[];
	env: Record<string, string | undefined>;
	exitCode?: number;
	stdout: { write(value: string): void };
	stderr: { write(value: string): void };
	exit(code?: number): never;
};

declare class Buffer {
	readonly length: number;
	static from(value: string): Buffer;
	static byteLength(value: string): number;
	static concat(chunks: Buffer[]): Buffer;
	toString(encoding?: string): string;
}

declare module "node:fs/promises" {
	export function readFile(path: string, encoding: "utf8"): Promise<string>;
}

declare module "node:https" {
	type RequestOptions = {
		protocol: "https:";
		hostname: string;
		port?: string;
		method: string;
		path: string;
		headers: Record<string, string | number>;
	};

	type IncomingMessage = {
		statusCode?: number;
		on(event: "data", listener: (chunk: Buffer) => void): void;
		on(event: "end" | "aborted", listener: () => void): void;
		on(event: "error", listener: (error: Error) => void): void;
		destroy(error?: Error): void;
	};

	type ClientRequest = {
		on(event: "error", listener: (error: Error) => void): void;
		setTimeout(timeoutMs: number, listener: () => void): void;
		destroy(error?: Error): void;
		write(data: string): void;
		end(): void;
	};

	type HttpsModule = {
		request(
			options: RequestOptions,
			callback: (response: IncomingMessage) => void,
		): ClientRequest;
	};

	const https: HttpsModule;
	export default https;
}

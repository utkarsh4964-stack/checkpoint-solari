import asyncio
import os

from solari_sandbox import SandboxClient


async def main():
    client = SandboxClient(
        api_key=os.environ["SOLARI_API_KEY"],
        base_url="https://api.getsolari.com",
    )

    sb = None

    try:
        sb = await client.create(
            template="base",
            timeout_ms=900_000,
        )

        print(
            "CREATED:",
            getattr(sb, "sandboxId", getattr(sb, "id", None)),
        )
        print("TYPE:", type(sb))

        await sb.connect()

        print("CONNECTED")

        result = await sb.commands.run(
            "echo",
            args=["checkpoint-test"],
        )

        print("COMMAND OBJECT:", type(result))
        print(
            "COMMAND EXIT:",
            getattr(
                result,
                "exitCode",
                getattr(result, "exit_code", None),
            ),
        )
        print("COMMAND STDOUT:", getattr(result, "stdout", ""))
        print("COMMAND STDERR:", getattr(result, "stderr", ""))

        print("TESTING SNAPSHOT...")

        snapshot = await sb.snapshot("checkpoint-test")

        print("SNAPSHOT SUCCESS:", snapshot)

    finally:
        if sb is not None:
            try:
                await sb.kill()
                print("SANDBOX KILLED")
            except Exception as e:
                print("KILL ERROR:", e)

        close = getattr(client, "close", None)
        if close:
            try:
                await close()
            except Exception as e:
                print("CLIENT CLOSE ERROR:", e)


asyncio.run(main())
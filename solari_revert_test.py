import asyncio
import os

from solari_sandbox import SandboxClient


BASE_URL = "https://api.getsolari.com"


async def main():
    client = SandboxClient(
        api_key=os.environ["SOLARI_API_KEY"],
        base_url=BASE_URL,
        call_timeout_ms=900_000,
    )

    sandbox = None

    try:
        print("1. Creating sandbox...")

        sandbox = await client.create(
            template="base",
            timeout_ms=900_000,
        )

        print("   Created:", sandbox.sandboxId)
        print("   Connected:", sandbox.connected)

        print("\n2. Connecting...")
        await sandbox.connect()
        print("   Connected:", sandbox.connected)

        print("\n3. Writing ORIGINAL using run_code()...")

        result = await sandbox.run_code(
            "open('/project/revert_test.txt', 'w').write('ORIGINAL\\n')"
        )

        print("   Result:", result)

        print("\n4. Creating snapshot...")

        snapshot_id = await sandbox.snapshot("before-change")

        print("   Snapshot:", snapshot_id)

        print("\n5. Changing file to CHANGED...")

        result = await sandbox.run_code(
            "open('/project/revert_test.txt', 'w').write('CHANGED\\n')"
        )

        print("   Result:", result)

        print("\n6. Reading file before revert...")

        result = await sandbox.run_code(
            "print(open('/project/revert_test.txt').read())"
        )

        print("   BEFORE REVERT:")
        print(result)

        print("\n7. REVERTING...")

        await sandbox.revert(snapshot_id)

        print("   REVERT CALL SUCCEEDED")

        print("\n8. Reading file after revert...")

        result = await sandbox.run_code(
            "print(open('/project/revert_test.txt').read())"
        )

        print("   AFTER REVERT:")
        print(result)

        print("\n======================================")
        print("SOLARI SNAPSHOT/REVERT TEST COMPLETE")
        print("======================================")

    except Exception as e:
        print("\n======================================")
        print("TEST FAILED")
        print("======================================")
        print("Type:", type(e).__name__)
        print("Message:", str(e))

    finally:
        if sandbox is not None:
            try:
                print("\n9. Killing sandbox...")
                await sandbox.kill()
                print("   Sandbox killed")
            except Exception as e:
                print(
                    "   Kill failed:",
                    type(e).__name__,
                    str(e),
                )

        try:
            await client.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
from dotenv import load_dotenv

load_dotenv()

from agent import MiniPlannerAgent
import asyncio
import sys
import os


def print_banner():
    print("=" * 60)
    print("Mini Planner Agent - 3D Blender Model Generator")
    print("=" * 60)
    print("Examples:")
    print("  • 'Make a medieval castle with towers'")
    print("  • 'Generate a sci-fi spaceship'")
    print("  • 'Design a modern house'")
    print("-" * 60)


def validate_environment():
    required_vars = ["GOOGLE_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Please set them in your .env file")
        return False
    return True


async def run_single_query():
    try:
        print_banner()

        if not validate_environment():
            return

        user_input = input("\nDescribe the 3D model you want to create: ").strip()

        if not user_input:
            print("Please provide a description!")
            return

        print(f"\nProcessing: '{user_input}'")
        print("This may take a few minutes...")
        print("-" * 60)

        agent = MiniPlannerAgent(max_steps=15)

        result = await agent.run_with_timeout(user_input, timeout_seconds=300)

        print("\n" + "=" * 60)
        print("FINAL RESULT:")
        print("=" * 60)
        print(result)

        summary = agent.get_execution_summary()
        print(f"\nExecution completed in {summary['total_steps']} steps")

        success_steps = sum(1 for s in summary['steps'] if s['success'])
        if success_steps > 0:
            print(f"{success_steps}/{summary['total_steps']} steps successful")

    except KeyboardInterrupt:
        print("\n\n Operation cancelled by user")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        print("Please check your configuration and try again.")


async def run_interactive_mode():
    print_banner()
    print("Interactive Mode - Type 'quit' or 'exit' to stop\n")

    if not validate_environment():
        return

    agent = MiniPlannerAgent(max_steps=15)
    conversation_count = 0

    try:
        while True:
            user_input = input(f"\n[{conversation_count + 1}] 🎨 Your request: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if not user_input:
                print("Please provide a description!")
                continue

            print(f"Processing: '{user_input}'")
            print("-" * 40)

            try:
                result = await agent.run_with_timeout(user_input, timeout_seconds=300)
                print(f"\nResult: {result}")

                # Clear state for next conversation
                agent.clear_state()
                conversation_count += 1

            except Exception as e:
                print(f"Error processing request: {str(e)}")
                agent.clear_state()  # Clear state even on error

    except KeyboardInterrupt:
        print("\n\nSession ended by user")


def show_help():
    """Show help information."""
    print("""
Blender Agent Help

Usage:
  python main.py [mode]

Modes:
  (no args)    - Single query mode (default)
  interactive  - Interactive conversation mode
  help        - Show this help

Environment Setup:
  Create a .env file with:
  GOOGLE_API_KEY=your_google_api_key_here

Examples:
  python main.py
  python main.py interactive
  python main.py help
""")


async def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "help":
            show_help()
            return
        elif mode == "interactive":
            await run_interactive_mode()
            return
        else:
            print(f"Unknown mode: {mode}")
            show_help()
            return

    await run_single_query()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)
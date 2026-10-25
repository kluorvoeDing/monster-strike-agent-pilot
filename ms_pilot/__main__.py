import argparse
import sys
from .core.client import iPhoneClient
from .core.physics import solve_2d_wall_bounce
from .modes.fast_farm import run_fast_farm_batch
from .modes.library_sweep import run_library_sweep
from .modes.copilot import CoPilotSession


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ms_pilot",
        description="Monster Strike Agent Pilot — 4-Mode Vision & Physics Controller",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # Mode 1: Fast-Farm (極速刷運極模式)
    p_farm = sub.add_parser("farm", help="Mode 1: Fast-Farming & Max-Luck (99) Sprint")
    p_farm.add_argument("--quest", nargs="+", default=["朝霧與夜櫻", "金烏玉兔", "遊馬"])
    p_farm.add_argument("--runs", type=int, default=5)
    p_farm.add_argument("--target-luck", type=int, default=99)
    p_farm.add_argument("--no-cans", action="store_true", help="Disable Stamina Can auto-recovery")
    p_farm.add_argument("--no-chest", action="store_true", help="Disable 2100-medal 寶箱+2 item")

    # Mode 2: Library Sweep (追憶書庫橫掃模式)
    p_lib = sub.add_parser("library", help="Mode 2: Library of Memories (追憶書庫) Sweep")
    p_lib.add_argument("--difficulty", default="極", choices=["極", "究極", "超絕"])
    p_lib.add_argument("--runs", type=int, default=10)
    p_lib.add_argument("--no-cans", action="store_true")

    # Mode 3: Tactical Boss Physics Solver Demo / Runner (高難度轟絕戰術模式)
    p_boss = sub.add_parser("boss-sim", help="Mode 3: 2D Wall-Bounce Raycast Solver Simulation")
    p_boss.add_argument("--start", type=float, nargs=2, default=[0.25, 0.55], metavar=("X0", "Y0"))
    p_boss.add_argument("--target", type=float, nargs=2, default=[0.50, 0.30], metavar=("XT", "YT"))
    p_boss.add_argument("--bounces", type=int, default=2, choices=[1, 2])

    # Mode 4: Co-Pilot (人機協作領航模式)
    p_cop = sub.add_parser("copilot", help="Mode 4: Human-in-the-Loop Co-Pilot Session")
    p_cop.add_argument("--quest", nargs="+", default=["朝霧與夜櫻", "遊馬"])
    p_cop.add_argument("--runs", type=int, default=3)
    p_cop.add_argument("--prefer-slot", type=int, choices=[1, 2, 3, 4], default=None)
    p_cop.add_argument("--no-chest", action="store_true")

    args = parser.parse_args()

    if args.mode == "boss-sim":
        sols = solve_2d_wall_bounce(
            start_pos=(args.start[0], args.start[1]),
            target_pos=(args.target[0], args.target[1]),
            bounces=args.bounces,
        )
        print(f"=== 2D Wall-Bounce Reflection Solutions: {args.start} -> {args.target} ===")
        for i, s in enumerate(sols, 1):
            print(
                f"  [{i}] {s['type']:<20} | Bounces: {s['bounces']} | "
                f"Launch Vec: ({s['ux']:+.3f}, {s['uy']:+.3f}) | Path Len: {s['path_length']:.3f}"
            )
        return 0

    with iPhoneClient() as client:
        if args.mode == "farm":
            run_fast_farm_batch(
                client,
                quest_keywords=args.quest,
                num_runs=args.runs,
                target_luck=args.target_luck,
                allow_stamina_cans=not args.no_cans,
                enable_extra_chest=not args.no_chest,
            )
        elif args.mode == "library":
            run_library_sweep(
                client,
                difficulty=args.difficulty,
                max_runs=args.runs,
                allow_stamina_cans=not args.no_cans,
            )
        elif args.mode == "copilot":
            session = CoPilotSession(
                client,
                prefer_slot=args.prefer_slot,
                enable_extra_chest=not args.no_chest,
            )
            session.run(quest_keywords=args.quest, runs=args.runs)

    return 0


if __name__ == "__main__":
    sys.exit(main())

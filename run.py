"""
Specification Resistance in Machine Shopping Behaviour
========================================================
Main entry point.

Usage:
    python run.py                                    # Pilot run
    python run.py --mode full                        # Full run
    python run.py --mode pilot --dry-run             # Dry run (no API calls)
    python run.py --mode pilot --conditions utility_explicit utility_override
    python run.py --mode full --no-webmall           # Skip WebMall assortments
    python run.py --analyze-only                     # Analysis on existing data
    python run.py --figures-only                     # Generate figures only
"""

import sys
import argparse
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_experiment_mode(args):
    """Run the specification resistance experiment."""
    from experiment import run_pilot, run_full
    from experiment.runner import run_single_model_full_suite
    from experiment.conditions import (
        list_conditions, core_conditions,
        utility_conditions, preference_conditions,
    )

    start_time = time.monotonic()

    print(f"\n{'='*70}")
    print(f"  SPECIFICATION RESISTANCE IN MACHINE SHOPPING BEHAVIOUR")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "data"

    # Resolve conditions
    conditions = None
    if args.conditions:
        conditions = args.conditions
    elif args.utility_only:
        conditions = utility_conditions()
    elif args.preference_only:
        conditions = preference_conditions()

    if args.mode == "suite":
        # Single-model full suite: every condition x every assortment
        results = run_single_model_full_suite(
            model_key=args.model or "gemini-2.5-flash",
            output_dir=output_dir,
            budget=args.budget,
            max_calls=args.max_calls,
            trials_per_condition=args.trials,
            dry_run=args.dry_run,
            enable_judge=not args.no_judge,
        )
    elif args.mode == "pilot":
        results = run_pilot(
            output_dir=output_dir,
            budget_per_provider=args.budget,
            max_calls_per_provider=args.max_calls,
            dry_run=args.dry_run,
            conditions=conditions,
            n_assortments_per_category=args.assortments_per_category,
        )
    elif args.mode == "full":
        results = run_full(
            output_dir=output_dir,
            budget_per_provider=args.budget,
            max_calls_per_provider=args.max_calls,
            trials_per_condition=args.trials,
            include_mechanisms=not args.no_mechanisms,
            include_webmall=not args.no_webmall,
            dry_run=args.dry_run,
        )
    else:
        print(f"ERROR: Unknown mode '{args.mode}'")
        sys.exit(1)

    duration = time.monotonic() - start_time

    print(f"\n{'='*70}")
    print(f"  EXPERIMENT COMPLETE")
    print(f"  Duration: {duration:.0f}s ({duration/60:.1f} min)")
    print(f"  Results: {len(results)} trials")
    print(f"{'='*70}")

    return results


def run_analysis(args):
    """Run statistical analysis on existing data."""
    from analysis.spec_resistance_analysis import run_spec_resistance_analysis

    data_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "data"
    results_dir = Path(args.results_dir) if args.results_dir else PROJECT_ROOT / "results"

    run_spec_resistance_analysis(
        data_dir=data_dir,
        output_dir=results_dir,
    )


def run_figures(args):
    """Generate figures from existing analysis results."""
    from analysis.resistance_figures import generate_all_resistance_figures

    results_dir = Path(args.results_dir) if args.results_dir else PROJECT_ROOT / "results"

    generate_all_resistance_figures(
        results_dir=results_dir,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Specification Resistance in Machine Shopping Behaviour",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                                    # Pilot run
  python run.py --mode suite                       # Full suite with Gemini 2.5 Flash
  python run.py --mode suite --model gpt-4o        # Full suite with GPT-4o
  python run.py --mode suite --dry-run             # Dry run (see trial count)
  python run.py --mode full --trials 5             # Full run, 5 trials/condition
  python run.py --analyze-only                     # Analysis only
  python run.py --figures-only                     # Figures only
  python run.py --conditions baseline utility_explicit utility_constrained
        """,
    )

    # Mode
    parser.add_argument("--mode", choices=["pilot", "full", "suite"], default="pilot",
                        help="Run mode: pilot, full, or suite (single model, all conditions)")
    parser.add_argument("--model", type=str, default=None,
                        help="Model key for suite mode (default: gemini-2.5-flash)")
    parser.add_argument("--no-judge", action="store_true",
                        help="Disable LLM-as-judge evaluation")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Skip experiment, run analysis on existing data")
    parser.add_argument("--figures-only", action="store_true",
                        help="Skip experiment and analysis, generate figures only")

    # Experiment parameters
    parser.add_argument("--budget", type=float, default=20.0,
                        help="Per-provider budget in USD (default: 20)")
    parser.add_argument("--max-calls", type=int, default=500,
                        help="Max API calls per provider (default: 500)")
    parser.add_argument("--trials", type=int, default=5,
                        help="Trials per condition for full mode (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would run without making API calls")

    # Condition filters
    parser.add_argument("--conditions", nargs="+", default=None,
                        help="Specific conditions to run")
    parser.add_argument("--utility-only", action="store_true",
                        help="Run only utility-based conditions")
    parser.add_argument("--preference-only", action="store_true",
                        help="Run only preference-based conditions")
    parser.add_argument("--no-mechanisms", action="store_true",
                        help="Skip mechanism isolation conditions")
    parser.add_argument("--no-webmall", action="store_true",
                        help="Skip WebMall-derived assortments")

    # Assortment control
    parser.add_argument("--assortments-per-category", type=int, default=1,
                        help="Assortments per category for pilot (default: 1)")

    # Output directories
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Data output directory")
    parser.add_argument("--results-dir", type=str, default=None,
                        help="Analysis results directory")

    args = parser.parse_args()

    if args.figures_only:
        run_figures(args)
    elif args.analyze_only:
        run_analysis(args)
    else:
        results = run_experiment_mode(args)
        if not args.dry_run and results:
            print("\n\nRunning analysis on collected data...\n")
            run_analysis(args)
            run_figures(args)


if __name__ == "__main__":
    main()

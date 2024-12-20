import argparse
import json
import logging
import os

from plotting.drawer import draw_gantt_chart
from solution_methods.cp_sat import FJSPmodel, FJSPmodel_stoch, FJSPSDSTmodel, JSPmodel
from solution_methods.cp_sat.utils import solve_model
from solution_methods.helper_functions import (
    load_job_shop_env,
    load_parameters,
    load_stochastic_job_shop_env,
)

logging.basicConfig(level=logging.INFO)
DEFAULT_RESULTS_ROOT = "./results/cp_sat"
PARAM_FILE = "configs/cp_sat_SD3_10x5+mix_det_1_1.toml"


def run_method(folder, exp_name, **kwargs):
    """
    Solve the scheduling problem for the provided input file.
    """

    if "fjsp_sdst" in str(kwargs["instance"]["problem_instance"]):
        jobShopEnv = load_job_shop_env(kwargs["instance"]["problem_instance"])
        model, vars = FJSPSDSTmodel.fjsp_sdst_cp_sat_model(jobShopEnv)
    elif "fjsp" in str(kwargs["instance"]["problem_instance"]):
        if not kwargs["instance"]["stoch"]:
            jobShopEnv = load_job_shop_env(kwargs["instance"]["problem_instance"])
            model, vars = FJSPmodel.fjsp_cp_sat_model(jobShopEnv)
        else:
            jobShopEnvs = load_stochastic_job_shop_env(
                kwargs["instance"]["problem_instance"],
                num_realizations=kwargs["instance"]["num_realizations"],
            )
            model, vars = FJSPmodel_stoch.fjsp_stoch_cp_sat_model(
                jobShopEnvs,
                obj=kwargs["instance"]["stoch_obj"],
                alpha=kwargs["instance"]["VaR_alpha"],
            )
    elif any(
        scheduling_problem in str(kwargs["instance"]["problem_instance"])
        for scheduling_problem in ["jsp", "fsp"]
    ):
        jobShopEnv = load_job_shop_env(kwargs["instance"]["problem_instance"])
        model, vars = JSPmodel.jsp_cp_sat_model(jobShopEnv)

    solver, status, solution_count = solve_model(model, kwargs["solver"]["time_limit"])

    # Update jobShopEnv with found solution
    if "fjsp_sdst" in str(kwargs["instance"]["problem_instance"]):
        jobShopEnv, results = FJSPSDSTmodel.update_env(
            jobShopEnv,
            vars,
            solver,
            status,
            solution_count,
            kwargs["solver"]["time_limit"],
        )
    elif "fjsp" in str(kwargs["instance"]["problem_instance"]):
        if not kwargs["instance"]["stoch"]:
            jobShopEnv, results = FJSPmodel.update_env(
                jobShopEnv,
                vars,
                solver,
                status,
                solution_count,
                kwargs["solver"]["time_limit"],
            )
        else:
            jobShopEnvs, results = FJSPmodel_stoch.update_envs(
                jobShopEnvs,
                vars,
                solver,
                status,
                solution_count,
                kwargs["solver"]["time_limit"],
            )
    elif "jsp" in str(kwargs["instance"]["problem_instance"]):
        jobShopEnv, results = JSPmodel.update_env(
            jobShopEnv,
            vars,
            solver,
            status,
            solution_count,
            kwargs["solver"]["time_limit"],
        )

    # Plot the ganttchart of the solution
    if kwargs["instance"]["stoch"]:
        for jobShopEnv in jobShopEnvs:
            if kwargs["output"]["plotting"]:
                draw_gantt_chart(jobShopEnv)
    else:
        if kwargs["output"]["plotting"]:
            draw_gantt_chart(jobShopEnv)

    # Ensure the directory exists; create if not
    dir_path = os.path.join(folder, exp_name)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Specify the full path for the file
    file_path = os.path.join(dir_path, "CP_results.json")

    # Save results to JSON (will create or overwrite the file)
    with open(file_path, "w") as outfile:
        json.dump(results, outfile, indent=4)


def main(param_file=PARAM_FILE):
    try:
        parameters = load_parameters(param_file)
    except FileNotFoundError:
        logging.error(f"Parameter file {param_file} not found.")
        return

    folder = DEFAULT_RESULTS_ROOT

    exp_name = "or_tools_" + str(
        parameters["solver"]["time_limit"]
    ) + "/" f"{'stoch_{}_{}{}'.format(parameters['instance']['num_realizations'], parameters['instance']['stoch_obj'], '_'+str(int(parameters['instance']['VaR_alpha'] * 100)) if parameters['instance']['stoch_obj']=='VaR' else '') if parameters['instance']['stoch']==True else ''}" + str(
        parameters["instance"]["problem_instance"]
    )

    run_method(folder, exp_name, **parameters)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OR-Tools CP-SAT")
    parser.add_argument(
        "--config_file",
        metavar="-f",
        type=str,
        nargs="?",
        default=PARAM_FILE,
        help="path to config file",
    )
    args = parser.parse_args()
    main(param_file=args.config_file)

# RCPSP-REQ: A Solver for Resource-Constrained Project Scheduling with Stakeholder Requirements

This repository contains a proof-of-concept implementation of the RCPSP-REQ solver, designed to address the Resource-Constrained Project Scheduling Problem (RCPSP) while incorporating diverse stakeholder requirements. The system is particularly geared towards applications like Urban Air Mobility (UAM) scheduling.

This software is developed as part of the research detailed in our paper:
**Title:** Enhancing Urban Air Mobility Scheduling Through Declarative Reasoning and Stakeholder Modeling
**Authors:** Jeongseok Kim and Kangjin Kim
*(Status: Under Review)*

## Overview

The solver framework consists of two main components:

1.  **Instance Generators:** Scripts to create RCPSP and RCPSP-REQ problem instances based on configurable parameters.
2.  **Instance Solvers:** Scripts to solve the generated instances using different methodologies, including Mixed-Integer Linear Programming (MILP) and Answer Set Programming (ASP).

## Prerequisites

Before running the scripts, ensure you have the following installed:

* **Python:** Version 3.8 or higher. (e.g., Python 3.12.3 from conda-forge).
* **For MILP Solver:**
    * PuLP library (e.g., version 2.8.0). Install via pip: `pip install pulp`
    * A CBC solver (COIN-OR Branch and Cut). PuLP will typically download a pre-compiled binary (PULP_CBC_CMD) if one is not found, or you can install it separately. If using Cygwin, ensure it's accessible in your PATH.
* **For ASP Solver:**
    * Clingo (Answer Set Programming system from Potassco). (e.g., version 5.7.1). Ensure Clingo is installed and accessible through your Python API. Installation instructions can be found on the [Potassco website](https://potassco.org/clingo/).
* **(Optional but Recommended):** A virtual environment tool like `venv` or `conda` to manage dependencies.

## Directory Structure
```bash
rcpsp-req-solver/
├── generator/
│   ├── generator_plain.py
│   ├── generator_req.py
│   ├── adding_reqs.py
│   ├── assign_req_trees.py
│   ├── instance.py
│   ├── mass.py
│   └── take_parts.py
├── solver/
│   ├── solve_milp.py
│   ├── solve_asp.py
│   ├── solve_plain.py
│   ├── solve_iter.py*
│   ├── solve_req.py*
│   ├── _asp_trim.lp
│   ├── _asp_trim_reqs.lp
│   ├── asp_form.py
│   ├── predicate.py
│   ├── preprocess.py
│   ├── rcpsp.py
│   ├── rcpsp_asp.py
│   ├── rcpsp_milp.py
│   ├── req1_rewritten4.lp
│   ├── req2_renamed7.lp
│   └── req3_renamed6.lp
├── instances/                # Directory for generated instances (to be created)
│── gencfg.json         	  # Configuration file (to be generated for the first time)
└── README.md
└── LICENSE.md
```

## Usage

### 1. Configuration

Both instance generators (`generator_plain.py` and `generator_req.py`) rely on a `gencfg.json` file (to be generated if you run it for the first time) located in the root directory. This JSON file defines parameters for instance generation, such as the number of jobs, resources, precedence relations, and specific stakeholder requirements for RCPSP-REQ.

* **Creating/Modifying `gencfg.json`:**
    * You can manually create or edit `gencfg.json` based on the expected structure.
    * Alternatively, the generator scripts might include functionality to create a default `gencfg.json` if one doesn't exist. Please clarify this or provide an example `gencfg.json`.

    **Example `gencfg.json` structure (illustrative):**
    ```json
    {
        "num_of_insts": 100, 			// for number of instances to be generated
		"inst_count_max": 5,			// for number of forests
        "task_max_count": 20, 			// for number of jobs in an instance
        "resource_type_count": 4,		// for number of resources
		"timeout": 600,					// for timeout
        // ... other parameters for plain RCPSP
        "stakeholder_requirements": { 	// For RCPSP-REQ
			"rstar": 1, 				// for the r^{\star} resource type
            // ... other requirement parameters
        }
    }
    ```

### 2. Generating Instances

Navigate to the `generator` directory to run the generation scripts. Generated instances will typically be saved to an output directory (`../instances/`).

**A. For Plain RCPSP Problems:**
```bash
cd generator
python generator_plain.py
```

This will generate instances based on gencfg.json and save them (e.g., as .lp files for ASP or other suitable formats).

**B. For RCPSP-REQ Problems:**
```bash
cd generator
python generator_req.py
```

This will generate instances incorporating stakeholder requirements, based on gencfg.json.

### 3. Solving Instances
Navigate to the solver directory to run the solving scripts. Ensure that the paths to the generated instance files are correctly specified within the solver scripts or passed as arguments.

**A. Solving Plain RCPSP Problems:**
* Using the MILP Method:
```bash
cd solver
python solve_milp.py
```

* Using the ASP Method:
```bash
cd solver
python solve_asp.py
```

**B. Solving RCPSP-REQ Problems:**
* Using the Plain RCPSP Solver (ASP) - (This implies solving the REQ instance without the iterative/specialized REQ handling, using the basic ASP RCPSP solver):
```bash
cd solver
python solve_plain.py
```

* Solving RCPSP-REQ Problems using the dedicated ASP-REQ solver for the single-pass REQ solver (Algorithm 1):
```bash
cd solver
python solve_req.py
```

* Solving RCPSP-REQ Problems using the dedicated ASP-REQ solver for the iterative REQ solver (Algorithm 2):
```bash
 python solve_iter.py
```

## Experimental Setup
The experiments detailed in our paper were conducted using:

* Python: Version 3.12.3 (conda-forge, AMD64)
* MILP Solver: PuLP library (version 2.8.0) with the CBC (COIN-OR Branch and Cut) solver (via PULP_CBC_CMD), within a Cygwin environment.
* ASP Solver: Clingo (version 5.7.1), within the same Python environment.
* Hardware: 11th Gen Intel(R) Core(TM) i5-1135G7 processor @ 2.40 GHz, 8GB RAM.
* Time Limit: 600 seconds per instance for all solution attempts.


## How to Cite
If you use this software or refer to our work, please cite our paper (details will be updated upon publication):

```
@article{KimKimUAM202X,
  title   = {Enhancing Urban Air Mobility Scheduling Through Declarative Reasoning and Stakeholder Modeling},
  author  = {Kim, Jeongseok and Kim, Kangjin},
  journal = {},
  year    = {},
  volume  = {},
  number  = {},
  pages   = {},
  doi     = {}
}
```


## Contributing

We welcome contributions! If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch (git checkout -b feature/your-feature-name).
3. Make your changes.
4. Commit your changes (git commit -m 'Add some feature').
5. Push to the branch (git push origin feature/your-feature-name).
6. Open a Pull Request.

Please ensure your code adheres to any existing coding standards and includes relevant tests if applicable.


## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). Refer the LICENSE.md file.


## Contact
For questions or feedback, please contact:

Jeongseok Kim - [jeongseok.kim@sk.com]
Kangjin Kim - [kangjinkim@cdu.ac.kr]

Or open an issue in this repository.

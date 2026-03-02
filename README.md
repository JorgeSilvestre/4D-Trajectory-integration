# 4D-Trajectory-integration

<figure align="center" >
<img src="docs/assets/placeholder.webp" width="400px"  alt="">
<figcaption></figcaption>
</figure>

## What is this repository

This repository collects materials related to the integration of enriched 4D trajectories in the field of air traffic management (ATM). This is a non-trivial problem, given that ATM-related data is currently scattered across different heterogeneous data sources that are difficult to integrate due to differences in data structure, nature, and quality.

Despite this, the availability of data in the context of ATM is key, and has gained relevance in recent years thanks to the progressive application of new technologies and advances in process monitoring and decision-making automation. The available data allows for comprehensive monitoring of the state of the airspace, enabling better operational performance in terms of safety, efficiency, and predictability.

To this end, an extraction, transformation, and loading (ETL) process is proposed that allows the necessary data to be acquired and transformed, and presented as enriched 4D trajectories that facilitate its exploitation in the context of air traffic management.

The materials and results shown in this repository are part of the doctoral thesis Improving efficiency of Trajectory-Based Operations for Air Traffic Management using Deep Learning (2025), whose main repository can be found here: 

[Link to the main repo](https://github.com/JorgeSilvestre/silvestre-thesis).

## Repository structure

The trajectoryIntegration package is the core of this repository, which contains several modules and sub-packages that implement the ETL pipeline. In addition, the following folders are included:

- `trajectoryIntegration`: Core pipeline.
- `docs`: Technical documentation of the ETL pipeline.
- `data`: 
- `reports`: 
- `test`: Several tests for the developed code.
- `visualization`: Contains several scripts to create Streamlit dashboards that enable data and quality metrics exploration and analysis.

<!-- → -->

## Quickstart

```pip install -r requirements.txt```

## Running the code

```python -m trajectoryIntegration```

def load_causal_model():
    import networkx as nx

    if not hasattr(nx.algorithms, "d_separated"):
        from networkx.algorithms.d_separation import is_d_separator

        setattr(nx.algorithms, "d_separated", is_d_separator)

    from dowhy import CausalModel

    return CausalModel

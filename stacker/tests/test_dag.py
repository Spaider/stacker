""" Tests on the DAG implementation """

from nose import with_setup
from nose.tools import nottest, raises
from stacker.dag import DAG, DAGValidationError
import multiprocessing

dag = None


@nottest
def blank_setup():
    global dag
    dag = DAG()


@nottest
def start_with_graph():
    global dag
    dag = DAG()
    dag.from_dict({'a': ['b', 'c'],
                   'b': ['d'],
                   'c': ['d'],
                   'd': []})


@with_setup(blank_setup)
def test_add_node():
    dag.add_node('a')
    assert dag.graph == {'a': set()}


@with_setup(start_with_graph)
def test_transpose():
    transposed = dag.transpose()
    assert transposed.graph == {'d': set(['c', 'b']),
                                'c': set(['a']),
                                'b': set(['a']),
                                'a': set([])}


@with_setup(blank_setup)
def test_add_edge():
    dag.add_node('a')
    dag.add_node('b')
    dag.add_edge('a', 'b')
    assert dag.graph == {'a': set('b'), 'b': set()}


@with_setup(blank_setup)
def test_from_dict():
    dag.from_dict({'a': ['b', 'c'],
                   'b': ['d'],
                   'c': ['d'],
                   'd': []})
    assert dag.graph == {'a': set(['b', 'c']),
                         'b': set('d'),
                         'c': set('d'),
                         'd': set()}


@with_setup(blank_setup)
def test_reset_graph():
    dag.add_node('a')
    assert dag.graph == {'a': set()}
    dag.reset_graph()
    assert dag.graph == {}


@with_setup(blank_setup)
def test_walk():
    dag = DAG()

    # b and c should be executed at the same time.
    dag.from_dict({'a': ['b', 'c'],
                   'b': ['d'],
                   'c': ['d'],
                   'd': []})

    lock = multiprocessing.Lock()  # Protects nodes from concurrent access
    nodes = []

    def walk_func(n):
        lock.acquire()
        nodes.append(n)
        lock.release()
        return True

    ok = dag.walk(walk_func)
    assert ok == True  # noqa: E712
    assert nodes == ['d', 'c', 'b', 'a'] or nodes == ['d', 'b', 'c', 'a']


@with_setup(blank_setup)
def test_walk_failed():
    dag = DAG()

    # b and c should be executed at the same time.
    dag.from_dict({'a': ['b', 'c'],
                   'b': ['d'],
                   'c': ['d'],
                   'd': []})

    lock = multiprocessing.Lock()  # Protects nodes from concurrent access
    nodes = []

    def walk_func(n):
        lock.acquire()
        nodes.append(n)
        lock.release()
        return False

    ok = dag.walk(walk_func)

    # Only 2 should have been hit. The rest are canceled because they depend on
    # the success of d.
    assert ok == False  # noqa: E712
    assert nodes == ['d']


@with_setup(start_with_graph)
def test_ind_nodes():
    assert dag.ind_nodes() == ['a']


@with_setup(blank_setup)
def test_topological_sort():
    dag.from_dict({'a': [],
                   'b': ['a'],
                   'c': ['b']})
    assert dag.topological_sort() == ['c', 'b', 'a']


@with_setup(start_with_graph)
def test_successful_validation():
    assert dag.validate()[0] == True  # noqa: E712


@raises(DAGValidationError)
@with_setup(blank_setup)
def test_failed_validation():
    dag.from_dict({'a': ['b'],
                   'b': ['a']})


@with_setup(start_with_graph)
def test_downstream():
    assert set(dag.downstream('a')) == set(['b', 'c'])


@with_setup(start_with_graph)
def test_all_downstreams():
    assert dag.all_downstreams('a') == ['c', 'b', 'd']
    assert dag.all_downstreams('b') == ['d']
    assert dag.all_downstreams('d') == []


@with_setup(start_with_graph)
def test_all_downstreams_pass_graph():
    dag2 = DAG()
    dag2.from_dict({'a': ['c'],
                    'b': ['d'],
                    'c': ['d'],
                    'd': []})
    assert dag2.all_downstreams('a') == ['c', 'd']
    assert dag2.all_downstreams('b') == ['d']
    assert dag2.all_downstreams('d') == []


@with_setup(start_with_graph)
def test_predecessors():
    assert set(dag.predecessors('a')) == set([])
    assert set(dag.predecessors('b')) == set(['a'])
    assert set(dag.predecessors('c')) == set(['a'])
    assert set(dag.predecessors('d')) == set(['b', 'c'])


@with_setup(start_with_graph)
def test_filter():
    dag2 = dag.filter(['b', 'c'])
    assert dag2.graph == {'b': set('d'),
                          'c': set('d'),
                          'd': set()}


@with_setup(start_with_graph)
def test_all_leaves():
    assert dag.all_leaves() == ['d']


@with_setup(start_with_graph)
def test_size():
    assert dag.size() == 4
    dag.delete_node('a')
    assert dag.size() == 3

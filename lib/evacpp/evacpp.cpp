#include <boost/shared_ptr.hpp>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

#include <iostream>
#include <unistd.h>

#define ia_status_created 0
#define ia_status_pending 1
#define ia_status_queued 2
#define ia_status_refused 3
#define ia_status_dead 4
#define ia_status_canceled 5
#define ia_status_ignored 6
#define ia_status_running 7
#define ia_status_failed 8
#define ia_status_terminated 9
#define ia_status_completed 10

class GenericAction {
    private:
        int _status;
    public:
        GenericAction() {
            _status = ia_status_created;
        }

        int get_status() {
            return _status;
        }

        void set_status(int status) {
            _status = status;
        }

        bool is_processed() {
            return ((_status != ia_status_created) && (_status != ia_status_pending));
        }

        bool is_finished() {
            return (
                    (_status == ia_status_refused) ||
                    (_status == ia_status_dead) ||
                    (_status == ia_status_canceled) ||
                    (_status == ia_status_ignored) ||
                    (_status == ia_status_failed) ||
                    (_status == ia_status_terminated) ||
                    (_status == ia_status_completed));
        }

        bool is_status_created() {
            return (_status == ia_status_created);
        }

        bool is_status_pending() {
            return (_status == ia_status_pending);
        }

        bool is_status_queued() {
            return (_status == ia_status_queued);
        }

        bool is_status_refused() {
            return (_status == ia_status_refused);
        }

        bool is_status_dead() {
            return (_status == ia_status_dead);
        }

        bool is_status_canceled() {
            return (_status == ia_status_canceled);
        }

        bool is_status_ignored() {
            return (_status == ia_status_ignored);
        }

        bool is_status_running() {
            return (_status == ia_status_running);
        }

        bool is_status_failed() {
            return (_status == ia_status_failed);
        }

        bool is_status_terminated() {
            return (_status == ia_status_terminated);
        }

        bool is_status_completed() {
            return (_status == ia_status_completed);
        }
};

bool action_wait_for_processed(GenericAction *a, float timeout, float delay) {
    Py_BEGIN_ALLOW_THREADS
    int i = 0;
    float wait_loops = timeout / delay;
    float ts = delay * 1000000;
    while (!a->is_processed() && (i++ < wait_loops)) {
        usleep(ts);
    }
    Py_END_ALLOW_THREADS
    return a->is_processed();
}

bool action_wait_for_finished(GenericAction *a, float timeout, float delay) {
    Py_BEGIN_ALLOW_THREADS
    int i = 0;
    float wait_loops = timeout / delay;
    float ts = delay * 1000000;
    while (!a->is_finished() && (i++ < wait_loops)) {
        usleep(ts);
    }
    Py_END_ALLOW_THREADS   
    return a->is_finished();
}

using namespace boost::python;

BOOST_PYTHON_MODULE(evacpp)
{
    def("action_wait_for_processed", &action_wait_for_processed);
    def("action_wait_for_finished", &action_wait_for_finished);
    class_<GenericAction>("GenericAction")
        .def("get_status", &GenericAction::get_status)
        .def("set_status", &GenericAction::set_status)
        .def("is_processed", &GenericAction::is_processed)
        .def("is_finished", &GenericAction::is_finished)
        .def("is_status_created", &GenericAction::is_status_created)
        .def("is_status_pending", &GenericAction::is_status_pending)
        .def("is_status_queued", &GenericAction::is_status_queued)
        .def("is_status_refused", &GenericAction::is_status_refused)
        .def("is_status_dead", &GenericAction::is_status_dead)
        .def("is_status_canceled", &GenericAction::is_status_canceled)
        .def("is_status_ignored", &GenericAction::is_status_ignored)
        .def("is_status_running", &GenericAction::is_status_running)
        .def("is_status_failed", &GenericAction::is_status_failed)
        .def("is_status_terminated", &GenericAction::is_status_terminated)
        .def("is_status_completed", &GenericAction::is_status_completed)
        ;
}

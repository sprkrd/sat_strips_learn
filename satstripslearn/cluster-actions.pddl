(define (domain cluster-actions)
  (:requirements :strips :equality :action-costs)
  (:types
    action-t section-t obj-t head-t - object
    obj-right-t obj-left-t - obj-t
  )
  (:constants
    pre add del - section-t
    action-left action-right - action-t
  )
  (:predicates
    (same-name ?obj-left - obj-left-t ?obj-right - obj-right-t)
    (matched ?o0 - obj-left-t ?o1 - obj-right-t)
    (unmatched ?o - obj-t)

    (atom-0 ?act - action-t ?sec - section-t ?h - head-t)
    (atom-1 ?act - action-t ?sec - section-t ?h - head-t ?o0 - obj-t)
    (atom-2 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 - obj-t)
    (atom-3 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 ?o2 - obj-t)

    (processed-atom-0 ?act - action-t ?sec - section-t ?h - head-t)
    (processed-atom-1 ?act - action-t ?sec - section-t ?h - head-t ?o0 - obj-t)
    (processed-atom-2 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 - obj-t)
    (processed-atom-3 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 ?o2 - obj-t)

    (taken-atom-0 ?act - action-t ?sec - section-t ?h - head-t)
    (taken-atom-1 ?act - action-t ?sec - section-t ?h - head-t ?o0 - obj-t)
    (taken-atom-2 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 - obj-t)
    (taken-atom-3 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 ?o2 - obj-t)

    (discarded-atom-0 ?act - action-t ?sec - section-t ?h - head-t)
    (discarded-atom-1 ?act - action-t ?sec - section-t ?h - head-t ?o0 - obj-t)
    (discarded-atom-2 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 - obj-t)
    (discarded-atom-3 ?act - action-t ?sec - section-t ?h - head-t ?o0 ?o1 ?o2 - obj-t)
  )
  (:functions
    (total-cost)
  )

  (:action match-same-name
   :parameters (?o0 - obj-left-t
                ?o1 - obj-right-t)
   :precondition (and
      (unmatched ?o0)
      (unmatched ?o1)
      (same-name ?o0 ?o1)
   )
   :effect (and
      (matched ?o0 ?o0)
      (not (unmatched ?o0))
      (not (unmatched ?o1))
      ;(increase (total-cost) 1)
   )
  )

  (:action match
   :parameters (?o0 - obj-left-t
                ?o1 - obj-right-t)
   :precondition (and
      (unmatched ?o0)
      (unmatched ?o1)
   )
   :effect (and
      (matched ?o0 ?o1)
      (not (unmatched ?o0))
      (not (unmatched ?o1))
      (increase (total-cost) 10)
   )
  )

  (:action discard-atom-0
   :parameters (?act - action-t
                ?sec - section-t
                ?h - head-t)
   :precondition (atom-0 ?act ?sec ?h)
   :effect (and
      (processed-atom-0 ?act ?sec ?h)
      (discarded-atom-0 ?act ?sec ?h)
      (increase (total-cost) 100)
   )
  )

  (:action discard-atom-1
   :parameters (?act - action-t
                ?sec - section-t
                ?h - head-t
                ?o0 - obj-t)
   :precondition (atom-1 ?act ?sec ?h ?o0)
   :effect (and
      (processed-atom-1 ?act ?sec ?h ?o0)
      (discarded-atom-1 ?act ?sec ?h ?o0)
      (increase (total-cost) 100)
   )
  )

  (:action discard-atom-2
   :parameters (?act - action-t
                ?sec - section-t
                ?h - head-t ?o0
                ?o1 - obj-t)
   :precondition (atom-2 ?act ?sec ?h ?o0 ?o1)
   :effect (and
      (processed-atom-2 ?act ?sec ?h ?o0 ?o1)
      (discarded-atom-2 ?act ?sec ?h ?o0 ?o1)
      (increase (total-cost) 100)
   )
  )

  (:action discard-atom-3
   :parameters (?act - action-t
                ?sec - section-t
                ?h - head-t
                ?o0 ?o1 ?o2 - obj-t)
   :precondition (atom-3 ?act ?sec ?h ?o0 ?o1 ?o2)
   :effect (and
      (processed-atom-3 ?act ?sec ?h ?o0 ?o1 ?o2)
      (discarded-atom-3 ?act ?sec ?h ?o0 ?o1 ?o2)
      (increase (total-cost) 100)
   )
  )

  (:action take-atom-0
   :parameters (?sec - section-t
                ?h - head-t)
   :precondition (and
      (atom-0 action-left ?sec ?h)
      (atom-0 action-right ?sec ?h)
   )
   :effect (and
      (processed-atom-0 action-left ?sec ?h)
      (processed-atom-0 action-right ?sec ?h)
      (taken-atom-0 action-left ?sec ?h)
      (taken-atom-0 action-right ?sec ?h)
   )
  )

  (:action take-atom-1
   :parameters (?sec - section-t
                ?h - head-t
                ?o0-left - obj-left-t
                ?o0-right - obj-right-t)
   :precondition (and
      (atom-1 action-left ?sec ?h ?o0-left)
      (atom-1 action-right ?sec ?h ?o0-right)
      (matched ?o0-left ?o0-right)
   )
   :effect (and
      (processed-atom-1 action-left ?sec ?h ?o0-left)
      (processed-atom-1 action-right ?sec ?h ?o0-right)
      (taken-atom-1 action-left ?sec ?h ?o0-left)
      (taken-atom-1 action-right ?sec ?h ?o0-right)
   )
  )

  (:action take-atom-2
   :parameters (?sec - section-t
                ?h - head-t
                ?o0-left ?o1-left - obj-left-t
                ?o0-right ?o1-right - obj-right-t)
   :precondition (and
      (atom-2 action-left ?sec ?h ?o0-left ?o1-left)
      (atom-2 action-right ?sec ?h ?o0-right ?o1-right)
      (matched ?o0-left ?o0-right)
      (matched ?o1-left ?o1-right)
   )
   :effect (and
      (processed-atom-2 action-left ?sec ?h ?o0-left ?o1-left)
      (processed-atom-2 action-right ?sec ?h ?o0-right ?o1-right)
      (taken-atom-2 action-left ?sec ?h ?o0-left ?o1-left)
      (taken-atom-2 action-right ?sec ?h ?o0-right ?o1-right)
   )
  )

  (:action take-atom-3
   :parameters (?sec - section-t
                ?h - head-t
                ?o0-left ?o1-left ?o2-left - obj-left-t
                ?o0-right ?o1-right ?o2-right - obj-right-t)
   :precondition (and
      (atom-3 action-left ?sec ?h ?o0-left ?o1-left ?o2-left)
      (atom-3 action-right ?sec ?h ?o0-right ?o1-right ?o2-right)
      (matched ?o0-left ?o0-right)
      (matched ?o1-left ?o1-right)
      (matched ?o2-left ?o2-right)
   )
   :effect (and
      (processed-atom-3 action-left ?sec ?h ?o0-left ?o1-left ?o2-left)
      (processed-atom-3 action-right ?sec ?h ?o0-right ?o1-right ?o2-right)
      (taken-atom-3 action-left ?sec ?h ?o0-left ?o1-left ?o2-left)
      (taken-atom-3 action-right ?sec ?h ?o0-right ?o1-right ?o2-right)
   )
  )
)




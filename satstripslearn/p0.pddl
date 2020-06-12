(define (problem p0)
  (:domain cluster-actions)
  (:objects
    l-loc-1-1 l-loc-1-2 l-loc-2-1 l-loc-2-2 l-left l-up l-right l-down - obj-left-t
    r-loc-1-1 r-loc-1-2 r-loc-2-1 r-loc-2-2 r-left r-up r-right r-down - obj-right-t
    adj at - head-t
  )
  (:init
    (= (total-cost) 0)

    (same-name l-loc-1-1 r-loc-1-1)
    (same-name l-loc-1-2 r-loc-1-2)
    (same-name l-loc-2-1 r-loc-2-1)
    (same-name l-loc-2-2 r-loc-2-2)
    (same-name l-left r-left)
    (same-name l-up r-up)
    (same-name l-right r-right)
    (same-name l-down r-down)

    (unmatched l-loc-1-1)
    (unmatched l-loc-1-2)
    (unmatched l-loc-2-1)
    (unmatched l-loc-2-2)
    (unmatched l-left)
    (unmatched l-up)
    (unmatched l-right)
    (unmatched l-down)

    (unmatched r-loc-1-1)
    (unmatched r-loc-1-2)
    (unmatched r-loc-2-1)
    (unmatched r-loc-2-2)
    (unmatched r-left)
    (unmatched r-up)
    (unmatched r-right)
    (unmatched r-down)

    ; action-left precondition 
    (atom-1 action-left pre at l-loc-1-1)
    (atom-3 action-left pre adj l-loc-1-1 l-loc-1-2 l-right)
    (atom-3 action-left pre adj l-loc-1-2 l-loc-1-1 l-left)
    (atom-3 action-left pre adj l-loc-1-1 l-loc-2-1 l-down)
    (atom-3 action-left pre adj l-loc-2-1 l-loc-1-1 l-up)
    (atom-3 action-left pre adj l-loc-1-2 l-loc-2-2 l-down)
    (atom-3 action-left pre adj l-loc-2-2 l-loc-1-2 l-up)
    (atom-3 action-left pre adj l-loc-2-1 l-loc-2-2 l-right)
    (atom-3 action-left pre adj l-loc-2-2 l-loc-2-1 l-left)
    ; action-left add
    (atom-1 action-left add at l-loc-1-2)
    ; action-right del
    (atom-1 action-left del at l-loc-1-1)

    ; action-right precondition 
    (atom-1 action-right pre at r-loc-1-2)
    (atom-3 action-right pre adj r-loc-1-1 r-loc-1-2 r-right)
    (atom-3 action-right pre adj r-loc-1-2 r-loc-1-1 r-left)
    (atom-3 action-right pre adj r-loc-1-1 r-loc-2-1 r-down)
    (atom-3 action-right pre adj r-loc-2-1 r-loc-1-1 r-up)
    (atom-3 action-right pre adj r-loc-1-2 r-loc-2-2 r-down)
    (atom-3 action-right pre adj r-loc-2-2 r-loc-1-2 r-up)
    (atom-3 action-right pre adj r-loc-2-1 r-loc-2-2 r-right)
    (atom-3 action-right pre adj r-loc-2-2 r-loc-2-1 r-left)
    ; action-right add
    (atom-1 action-right add at r-loc-2-2)
    ; action-right del
    (atom-1 action-right del at r-loc-1-2)
  )
  (:goal
    (and
      ; action-left precondition 
      (processed-atom-1 action-left pre at l-loc-1-1)
      (processed-atom-3 action-left pre adj l-loc-1-1 l-loc-1-2 l-right)
      (processed-atom-3 action-left pre adj l-loc-1-2 l-loc-1-1 l-left)
      (processed-atom-3 action-left pre adj l-loc-1-1 l-loc-2-1 l-down)
      (processed-atom-3 action-left pre adj l-loc-2-1 l-loc-1-1 l-up)
      (processed-atom-3 action-left pre adj l-loc-1-2 l-loc-2-2 l-down)
      (processed-atom-3 action-left pre adj l-loc-2-2 l-loc-1-2 l-up)
      (processed-atom-3 action-left pre adj l-loc-2-1 l-loc-2-2 l-right)
      (processed-atom-3 action-left pre adj l-loc-2-2 l-loc-2-1 l-left)
      ; action-left add
      (taken-atom-1 action-left add at l-loc-1-2)
      ; action-right del
      (taken-atom-1 action-left del at l-loc-1-1)

      ; action-right precondition 
      (processed-atom-1 action-right pre at r-loc-1-2)
      (processed-atom-3 action-right pre adj r-loc-1-1 r-loc-1-2 r-right)
      (processed-atom-3 action-right pre adj r-loc-1-2 r-loc-1-1 r-left)
      (processed-atom-3 action-right pre adj r-loc-1-1 r-loc-2-1 r-down)
      (processed-atom-3 action-right pre adj r-loc-2-1 r-loc-1-1 r-up)
      (processed-atom-3 action-right pre adj r-loc-1-2 r-loc-2-2 r-down)
      (processed-atom-3 action-right pre adj r-loc-2-2 r-loc-1-2 r-up)
      (processed-atom-3 action-right pre adj r-loc-2-1 r-loc-2-2 r-right)
      (processed-atom-3 action-right pre adj r-loc-2-2 r-loc-2-1 r-left)
      ; action-right add
      (taken-atom-1 action-right add at r-loc-2-2)
      ; action-right del
      (taken-atom-1 action-right del at r-loc-1-2)
    )
  )
  (:metric minimize (total-cost))
)

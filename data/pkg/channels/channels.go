package channels

import "sync"

// FanIn - сливает данные из нескольких входящих каналов в один исходящий.
//
// Если все входящие каналы закрываются, то закрывается исходящий.
func FanIn[T any](in ...<-chan T) <-chan T {
	out := make(chan T)

	var wg sync.WaitGroup
	wg.Add(len(in))

	go func() {
		wg.Wait()
		close(out)
	}()

	for _, c := range in {
		c := c

		go func() {
			defer wg.Done()

			for v := range c {
				out <- v
			}
		}()
	}

	return out
}

// FanOut - копирует данные из одного входящего канала в несколько исходящих.
//
// Если входящий канал закрывается, то закрываются все исходящие.
func FanOut[T any](in <-chan T, n int) []chan T {
	out := make([]chan T, 0, n)

	for i := 0; i < n; i++ {
		out = append(out, make(chan T))
	}

	go func() {
		var wg sync.WaitGroup

		defer func() {
			wg.Wait()

			for _, c := range out {
				close(c)
			}
		}()

		for v := range in {
			for _, c := range out {
				c := c

				wg.Add(1)

				go func() {
					defer wg.Done()
					c <- v
				}()
			}
		}
	}()

	return out
}

import asyncio
from asyncio import Semaphore, BoundedSemaphore


async def demo_semaphore_basic():
	"""
	演示基本的 Semaphore 使用
	Semaphore 用于控制同时访问某个资源的协程数量
	"""
	print("=== Semaphore 基本使用演示 ===")

	# 创建一个信号量，允许最多3个协程同时访问
	semaphore = Semaphore(3)

	async def worker(name, work_time):
		# 使用 async with 自动管理信号量的获取和释放
		async with semaphore:
			print(f"Worker {name} 开始工作，将持续 {work_time} 秒")
			await asyncio.sleep(work_time)
			print(f"Worker {name} 完成工作")

	# 创建多个工作任务
	tasks = [worker("A", 2), worker("B", 1), worker("C", 3), worker("D", 1), worker("E", 2)]

	print("注意：虽然创建了5个worker，但由于信号量限制为3，同一时间最多只有3个在执行")
	await asyncio.gather(*tasks)
	print("所有工作完成！\n")


async def demo_semaphore_vs_bounded():
	"""
	演示 Semaphore 和 BoundedSemaphore 的关键区别
	BoundedSemaphore 会检查释放次数是否超过获取次数
	"""
	print("=== Semaphore vs BoundedSemaphore 区别演示 ===")

	# 普通 Semaphore - 可以过度释放
	regular_sem = Semaphore(2)
	await regular_sem.acquire()
	print(f"普通Semaphore获取后值: {regular_sem._value}")

	# 过度释放 - 普通Semaphore允许这样做
	regular_sem.release()
	regular_sem.release()  # 多释放一次！
	print(f"普通Semaphore过度释放后值: {regular_sem._value} (超过了初始值)")

	# BoundedSemaphore - 不允许过度释放
	bounded_sem = BoundedSemaphore(2)
	await bounded_sem.acquire()
	print(f"BoundedSemaphore获取后值: {bounded_sem._value}")

	bounded_sem.release()
	print(f"BoundedSemaphore正常释放后值: {bounded_sem._value}")

	try:
		bounded_sem.release()  # 尝试过度释放
		print("这行不会被执行")
	except ValueError as e:
		print(f"BoundedSemaphore过度释放抛出异常: {e}")

	print()


async def demo_deadlock_scenario():
	"""
	演示由于忘记释放信号量导致的死锁情况
	"""
	print("=== 信号量死锁场景演示 ===")

	semaphore = Semaphore(2)

	async def problematic_worker(name):
		print(f"Worker {name} 尝试获取信号量...")
		await semaphore.acquire()
		print(f"Worker {name} 获取到信号量，开始工作")
		# 注意：这里故意不释放信号量！
		# 在实际代码中应该使用 async with 或确保释放

	# 创建工作任务
	tasks = [problematic_worker("1"), problematic_worker("2"), problematic_worker("3")]  # 这个会永远等待！

	# 设置超时，避免程序永远挂起
	try:
		await asyncio.wait_for(asyncio.gather(*tasks), timeout=3.0)
	except asyncio.TimeoutError:
		print("检测到死锁！第三个worker永远无法获取信号量")
		print("解决方案：总是使用 async with 或确保在finally块中释放信号量\n")


async def demo_proper_usage():
	"""
	演示信号量的正确使用方法
	"""
	print("=== 信号量正确使用方式演示 ===")

	semaphore = Semaphore(2)  # 限制同时访问数为2

	async def proper_worker(name, work_time):
		# 方法1：使用 async with（推荐）
		async with semaphore:
			print(f"Worker {name} 开始工作")
			await asyncio.sleep(work_time)
			print(f"Worker {name} 完成工作")

	async def proper_worker_manual(name, work_time):
		# 方法2：手动管理，使用 try-finally 确保释放
		await semaphore.acquire()
		try:
			print(f"Worker {name} 开始工作")
			await asyncio.sleep(work_time)
			print(f"Worker {name} 完成工作")
		finally:
			semaphore.release()

	tasks = [proper_worker("A", 1), proper_worker("B", 2), proper_worker_manual("C", 1), proper_worker_manual("D", 1)]

	await asyncio.gather(*tasks)
	print("所有工作正常完成，没有死锁！\n")


async def demo_concurrent_downloads():
	"""
	实际应用示例：模拟限制并发下载数量
	"""
	print("=== 实际应用：限制并发下载数量 ===")

	# 模拟最多3个并发下载
	download_semaphore = Semaphore(3)

	async def download_file(filename, size):
		async with download_semaphore:
			print(f"开始下载: {filename} (大小: {size}MB)")
			# 模拟下载时间，与文件大小成正比
			await asyncio.sleep(size * 0.1)
			print(f"下载完成: {filename}")
			return f"{filename}_content"

	# 模拟多个文件下载
	files = [
		("document.pdf", 5),
		("image.jpg", 2),
		("video.mp4", 10),
		("archive.zip", 3),
		("music.mp3", 4),
		("backup.tar", 6),
	]

	download_tasks = [download_file(name, size) for name, size in files]
	results = await asyncio.gather(*download_tasks)

	print(f"所有下载完成！共下载了 {len(results)} 个文件")
	print("通过信号量限制，避免了同时发起过多网络请求\n")


async def main():
	"""
	主函数，运行所有的演示示例
	"""
	print("🚀 Python asyncio Semaphore 教学演示")
	print("=" * 50)

	# 运行各个演示
	await demo_semaphore_basic()  # 基本使用
	await demo_semaphore_vs_bounded()  # 两种信号量区别
	await demo_deadlock_scenario()  # 死锁演示
	await demo_proper_usage()  # 正确用法
	await demo_concurrent_downloads()  # 实际应用

	print("🎓 教学总结：")
	print("1. Semaphore 用于限制并发访问数量")
	print("2. 使用 async with 自动管理信号量，避免忘记释放")
	print("3. BoundedSemaphore 提供额外的安全检查")
	print("4. 在实际应用中可用于限制网络请求、文件操作等并发数量")


if __name__ == "__main__":
	asyncio.run(main())
